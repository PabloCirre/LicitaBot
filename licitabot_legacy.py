#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Radar licitaciones web (PLACSP sindicacion_643) -> filtra por keywords -> envía email SMTP (SSL 465) -> hace GET al detalle.

Requisitos:
  pip install feedparser requests

Config (sin contraseña):
  SMTP_HOST=mail.centraldecomunicacion.es
  SMTP_PORT=465
  SMTP_USER=licitador@centraldecomunicacion.es
  SMTP_PASS=TU_PASSWORD   <-- falta a propósito
  MAIL_FROM=licitador@centraldecomunicacion.es
  MAIL_TO=centraldecomunicaciom@gmail.com
"""

import os
import ssl
import time
import sqlite3
import logging
import argparse
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import requests
import feedparser

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


FEED_URL_DEFAULT = (
    "https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/"
    "licitacionesPerfilesContratanteCompleto3.atom"
)

# Keywords principales + secundarias (idénticas a tu n8n, con soporte de acentos)
WEB_KEYWORDS = [
    "web",
    "página web",
    "paginas web",
    "páginas web",
    "sitio web",
    "web corporativa",
    "web institucional",
    "plataforma web",
    "webform",
    "tienda online",
    "ecommerce",
    "comercio electrónico",
]
EXTRA_KEYWORDS = ["intranet", "extranet"]


@dataclass(frozen=True)
class FeedItem:
    title: str
    summary: str
    link: str
    date_str: str


def normalize_text(s: str) -> str:
    """Minúsculas + quita acentos + colapsa espacios."""
    if not s:
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = " ".join(s.split())
    return s


def find_match_keyword(title: str, summary: str) -> Optional[str]:
    """Devuelve la primera keyword que matchea (para explicar el 'por qué')."""
    t = normalize_text(title)
    su = normalize_text(summary)

    for k in WEB_KEYWORDS:
        kk = normalize_text(k)
        if kk in t or kk in su:
            return k

    for k in EXTRA_KEYWORDS:
        kk = normalize_text(k)
        if kk in t or kk in su:
            return k

    return None


def ensure_db(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen (
            link TEXT PRIMARY KEY,
            first_seen_utc TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def already_seen(conn: sqlite3.Connection, link: str) -> bool:
    cur = conn.execute("SELECT 1 FROM seen WHERE link = ? LIMIT 1", (link,))
    return cur.fetchone() is not None


def mark_seen(conn: sqlite3.Connection, link: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO seen(link, first_seen_utc) VALUES (?, ?)",
        (link, now),
    )
    conn.commit()


def parse_feed(feed_url: str) -> List[FeedItem]:
    d = feedparser.parse(feed_url)

    if getattr(d, "bozo", False):
        exc = getattr(d, "bozo_exception", None)
        raise RuntimeError(f"Error parseando feed (bozo): {exc}")

    items: List[FeedItem] = []
    for e in getattr(d, "entries", []):
        title = (e.get("title") or "").strip()
        summary = (e.get("summary") or "").strip()
        link = (e.get("link") or "").strip()
        date_str = (e.get("published") or e.get("updated") or "").strip()
        if not link:
            continue
        items.append(FeedItem(title=title, summary=summary, link=link, date_str=date_str))

    return items


def build_subject_body(item: FeedItem, matched_keyword: Optional[str]) -> Tuple[str, str]:
    # Personalidad "LicitaRadar 2.0" (texto, sin iconos/emojis)
    subject = f"LicitaRadar 2.0 | Nueva licitación web (PLACSP 643): {item.title}"

    lines: List[str] = []
    lines.append("Bipbip. Soy Licitabot.")
    lines.append("He detectado una licitación que huele a web/portal. Te la dejo lista para revisar.")
    lines.append("")
    lines.append("Datos rápidos")
    lines.append("--------------------------------")
    lines.append(f"Título: {item.title}")
    if item.date_str:
        lines.append(f"Fecha: {item.date_str}")
    if matched_keyword:
        lines.append(f"Motivo del aviso: coincide con keyword -> {matched_keyword}")

    if item.summary:
        lines.append("")
        lines.append("Resumen (del feed)")
        lines.append("--------------------------------")
        lines.append(item.summary)

    if item.link:
        lines.append("")
        lines.append("URL detalle")
        lines.append("--------------------------------")
        lines.append(item.link)

    lines.append("")
    lines.append("Siguiente paso sugerido")
    lines.append("--------------------------------")
    lines.append("1) Abre la URL de detalle y confirma objeto/alcance.")
    lines.append("2) Si encaja, lo metemos en pipeline (análisis + respuesta).")
    lines.append("")
    lines.append("Fuente: Sindicación 643 – Perfiles del contratante (PLACSP).")
    lines.append("LicitaRadar 2.0 (modo radar horario).")

    body = "\n".join(lines)
    return subject, body


def build_email_mime(
    mail_from: str,
    mail_to: str,
    subject: str,
    body_text: str,
    url_principal: str,
    matched_keyword: Optional[str],
) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Subject"] = subject

    mk = matched_keyword or "n/a"
    html = f"""<h2>LicitaRadar 2.0</h2>
<p>Bipbip. He detectado una licitación que parece de web/portal. Te la dejo ordenada.</p>

<h3>Variables del flujo</h3>
<p><strong>url_principal:</strong><br>{url_principal}</p>
<p><strong>keyword detectada:</strong><br>{mk}</p>

<hr>

<h3>Cuerpo detallado</h3>
<pre style="white-space: pre-wrap; font-family: monospace;">{body_text}</pre>
"""

    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def send_email_ssl_465(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    msg: MIMEMultipart,
    timeout: int = 25,
) -> None:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=timeout) as server:
        if smtp_user:
            server.login(smtp_user, smtp_pass)
        server.sendmail(msg["From"], [msg["To"]], msg.as_string())


def safe_filename_from_url(url: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    h = abs(hash(url))
    return f"placsp_{ts}_{h}.html"


def fetch_detail(
    session: requests.Session,
    url: str,
    timeout: int = 25,
    save_dir: Optional[str] = None,
) -> int:
    if not url:
        return 0

    r = session.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "LicitaRadar/2.0"},
        allow_redirects=True,
    )
    status = r.status_code

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, safe_filename_from_url(url))
        with open(path, "wb") as f:
            f.write(r.content)

    return status


def run_once(args: argparse.Namespace) -> None:
    conn = ensure_db(args.db)

    session = requests.Session()
    session.headers.update({"User-Agent": "LicitaRadar/2.0"})

    feed_items = parse_feed(args.feed_url)
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
                status = fetch_detail(
                    session,
                    item.link,
                    timeout=args.http_timeout,
                    save_dir=args.save_html_dir if args.save_html else None,
                )
                logging.info("DRY RUN: detalle %s -> HTTP %s", item.link, status)
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
            status = fetch_detail(
                session,
                item.link,
                timeout=args.http_timeout,
                save_dir=args.save_html_dir if args.save_html else None,
            )
            logging.info("Detalle %s -> HTTP %s", item.link, status)

        mark_seen(conn, item.link)

    logging.info("OK. Nuevos: %d | Matchean: %d | Emails: %d", new_items, matched, emailed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Licitabot bipbip: PLACSP 643 -> filtro web -> email SMTP SSL 465")
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


if __name__ == "__main__":
    main()
