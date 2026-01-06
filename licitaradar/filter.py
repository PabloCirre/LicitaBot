import unicodedata
from typing import Optional
from .config import WEB_KEYWORDS, EXTRA_KEYWORDS

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
