from datetime import datetime, timezone
import unicodedata
import re
import os
import glob

def normalize_filename(s: str) -> str:
    """Convierte un string arbitraio en un nombre de archivo seguro."""
    if not s:
        return "sin_titulo"
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # Reemplazar no-alfanuméricos con guiones solapados
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:120]  # Limite para dejar espacio a fecha + número


def get_next_sequence_number(base_dir: str, date_prefix: str) -> int:
    """
    Obtiene el siguiente número de secuencia para una fecha dada.
    Busca carpetas existentes con el patrón YYYY-MM-DD_NNN_* y devuelve NNN+1.
    """
    pattern = os.path.join(base_dir, f"{date_prefix}_*")
    existing = glob.glob(pattern)
    
    if not existing:
        return 1
    
    max_num = 0
    for folder in existing:
        folder_name = os.path.basename(folder)
        # Extraer el número: YYYY-MM-DD_NNN_resto
        match = re.match(rf"{re.escape(date_prefix)}_(\d+)_", folder_name)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)
    
    return max_num + 1


def get_safe_project_name(title: str, url: str, base_dir: str = "./data/licitaciones") -> str:
    """
    Genera un nombre de carpeta con formato: YYYY-MM-DD_NNN_titulo-corto
    Ejemplo: 2026-01-06_001_sistema-control-presencia
    
    Args:
        title: Título de la licitación
        url: URL de la licitación (para hash de unicidad)
        base_dir: Directorio base donde se crean las carpetas
    """
    # Fecha actual
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Nombre seguro del título (limitado para legibilidad)
    safe_title = normalize_filename(title)
    
    # Obtener siguiente número de secuencia
    os.makedirs(base_dir, exist_ok=True)
    seq_num = get_next_sequence_number(base_dir, today)
    
    # Formato: YYYY-MM-DD_NNN_titulo-corto
    return f"{today}_{seq_num:03d}_{safe_title}"


def safe_filename_from_url(url: str) -> str:
    """LEGACY: Se mantiene por compatibilidad si algo lo usa, pero preferimos get_safe_project_name."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    h = abs(hash(url))
    return f"placsp_{ts}_{h}.html"

