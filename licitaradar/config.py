import os

FEED_URL_DEFAULT = (
    "https://contrataciondelsectorpublico.gob.es/sindicacion/sindicacion_643/"
    "licitacionesPerfilesContratanteCompleto3.atom"
)

# Cargar keywords desde variable de entorno (separadas por comas)
# Ejemplo: KEYWORDS="web, app, ia"
_env_keywords = os.getenv("KEYWORDS", "")
if _env_keywords:
    WEB_KEYWORDS = [k.strip() for k in _env_keywords.split(",") if k.strip()]
else:
    WEB_KEYWORDS = [
        "web",
        "plataforma",
        "app",
        "inteligencia artificial",
        "datos"
    ]

EXTRA_KEYWORDS = ["intranet", "extranet"]
