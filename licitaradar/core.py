import argparse
import logging
import os
import requests
import time
from .config import FEED_URL_DEFAULT
from .database import ensure_db, already_seen, mark_seen
from .fetcher import parse_feed
from .browser_crawler import procesar_licitacion
from .filter import find_match_keyword
from .notifier import build_subject_body, build_email_mime, send_email_ssl_465

def run_once(args: argparse.Namespace) -> None:
    conn = ensure_db(args.db)

    session = requests.Session()
    session.headers.update({"User-Agent": "LicitaRadar/2.0"})

    try:
        feed_items = parse_feed(args.feed_url)
    except Exception as e:
        logging.error(f"Error parsing feed: {e}")
        return

    logging.info("Feed leído. Items: %d", len(feed_items))

    new_items = 0
    matched = 0
    emailed = 0

    for item in feed_items:
        if already_seen(conn, item.link):
            continue

        new_items += 1

        matched_keyword = find_match_keyword(item.title, item.summary)
        if not matched_keyword:
            if args.mark_nonmatching_as_seen:
                mark_seen(conn, item.link)
            continue

        matched += 1

        subject, body = build_subject_body(item, matched_keyword)
        msg = build_email_mime(
            mail_from=args.mail_from,
            mail_to=args.mail_to,
            subject=subject,
            body_text=body,
            url_principal=item.link,
            matched_keyword=matched_keyword,
        )

        if args.dry_run:
            logging.info("DRY RUN: enviaría email: %s", subject)
            if args.fetch_detail:
                base_dir = args.save_html_dir if args.save_html else "./data/licitaciones"
                
                # Usar browser_crawler para extraer enlaces
                result = procesar_licitacion(
                    url=item.link,
                    titulo=item.title,
                    keyword=matched_keyword,
                    base_dir=base_dir
                )
                
                # Output simplificado
                print(f"\n{'='*60}")
                print(f"LICITACION: {item.title}")
                print(f"CARPETA: {result['project_name']}")
                print(f"PDFs: {len(result['pdfs'])}")
                print(f"Documentos: {len(result['documentos'])}")
                print(f"Enlaces totales: {len(result['enlaces'])}")
                print(f"{'='*60}\n")
                
                logging.info("DRY RUN: Guardado en %s", result['project_dir'])
            continue

        send_email_ssl_465(
            smtp_host=args.smtp_host,
            smtp_port=args.smtp_port,
            smtp_user=args.smtp_user,
            smtp_pass=args.smtp_pass,
            msg=msg,
            timeout=args.smtp_timeout,
        )
        emailed += 1
        logging.info("Email enviado: %s", subject)

        if args.fetch_detail:
            base_dir = args.save_html_dir if args.save_html else "./data/licitaciones"
            
            # Usar browser_crawler para extraer enlaces
            result = procesar_licitacion(
                url=item.link,
                titulo=item.title,
                keyword=matched_keyword,
                base_dir=base_dir
            )
            
            logging.info("Procesado: %s -> PDFs: %d, Docs: %d (Guardado en %s)", 
                        item.title[:50], len(result['pdfs']), len(result['documentos']), result['project_dir'])

        mark_seen(conn, item.link)

    logging.info("OK. Nuevos: %d | Matchean: %d | Emails: %d", new_items, matched, emailed)

def main_loop() -> None:
    parser = argparse.ArgumentParser(description="LicitaRadar 2.0: PLACSP 643 -> filtro web -> email SMTP SSL 465")
    parser.add_argument("--feed-url", default=FEED_URL_DEFAULT)
    parser.add_argument("--db", default="./data/seen.sqlite3")

    parser.add_argument("--smtp-host", default=os.getenv("SMTP_HOST", "mail.centraldecomunicacion.es"))
    parser.add_argument("--smtp-port", type=int, default=int(os.getenv("SMTP_PORT", "465")))
    parser.add_argument("--smtp-user", default=os.getenv("SMTP_USER", "licitador@centraldecomunicacion.es"))
    parser.add_argument("--smtp-pass", default=os.getenv("SMTP_PASS", ""))  # Falta a propósito

    parser.add_argument("--mail-from", default=os.getenv("MAIL_FROM", "licitador@centraldecomunicacion.es"))
    parser.add_argument("--mail-to", default=os.getenv("MAIL_TO", "centraldecomunicaciom@gmail.com"))

    parser.add_argument("--fetch-detail", action="store_true", default=True)
    parser.add_argument("--no-fetch-detail", action="store_false", dest="fetch_detail")

    parser.add_argument("--save-html", action="store_true", default=False)
    parser.add_argument("--save-html-dir", default="./data/html")

    parser.add_argument("--mark-nonmatching-as-seen", action="store_true", default=False)

    parser.add_argument("--smtp-timeout", type=int, default=25)
    parser.add_argument("--http-timeout", type=int, default=25)

    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--daemon", action="store_true", default=False)
    parser.add_argument("--interval-seconds", type=int, default=3600)

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.smtp_host:
        raise SystemExit("Falta SMTP_HOST / --smtp-host")

    if not args.dry_run and not args.smtp_pass:
        raise SystemExit("Falta SMTP_PASS (contraseña SMTP). Ponla como variable de entorno o --smtp-pass.")

    if not args.daemon:
        run_once(args)
        return

    logging.info("Modo daemon ON. Intervalo: %ds", args.interval_seconds)
    while True:
        try:
            run_once(args)
        except Exception as e:
            logging.exception("Error en ejecución: %s", e)
        time.sleep(args.interval_seconds)
