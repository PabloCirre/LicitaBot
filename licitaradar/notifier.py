import smtplib
import ssl
from typing import Tuple, Optional, List
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .fetcher import FeedItem

def build_subject_body(item: FeedItem, matched_keyword: Optional[str]) -> Tuple[str, str]:
    # Personalidad "LicitaRadar 2.0" (texto, sin iconos/emojis)
    subject = f"LicitaRadar 2.0 | Nueva licitación web (PLACSP 643): {item.title}"

    lines: List[str] = []
    lines.append("Soy LicitaRadar 2.0.")
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
    lines.append("LicitaRadar 2.0.")

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
<p>Soy LicitaRadar 2.0. He detectado una licitación que parece de web/portal. Te la dejo ordenada.</p>

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
