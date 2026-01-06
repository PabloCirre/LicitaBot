import os
import requests
import feedparser
from typing import List, Optional, Tuple
from dataclasses import dataclass
from .utils import safe_filename_from_url

@dataclass(frozen=True)
class FeedItem:
    title: str
    summary: str
    link: str
    date_str: str

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

import re
from urllib.parse import urljoin

def extract_pdf_links(html: str, base_url: str) -> List[str]:
    """Busca todos los enlaces a archivos .pdf en el HTML y los devuelve como URLs absolutas."""
    if not html:
        return []
    # Buscar patrones href="...pdf" o href='...pdf'
    # Intentamos ser generosos con las comillas y espacios
    pattern = r'href\s*=\s*["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']'
    matches = re.findall(pattern, html, re.IGNORECASE)
    
    # Convertir a absolutas y quitar duplicados
    links = set()
    for m in matches:
        links.add(urljoin(base_url, m))
    
    return sorted(list(links))

def fetch_detail(
    session: requests.Session,
    url: str,
    timeout: int = 25,
    save_dir: Optional[str] = None,
) -> Tuple[int, List[str]]:
    """Devuelve (status_code, list_of_pdf_links)."""
    if not url:
        return 0, []

    try:
        r = session.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "LicitaRadar/2.0"},
            allow_redirects=True,
        )
        status = r.status_code
        html_content = r.text
        
        pdf_links = extract_pdf_links(html_content, url)

        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            path = os.path.join(save_dir, "detalle.html")
            with open(path, "wb") as f:
                f.write(r.content)
                
        return status, pdf_links
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return 0, []
