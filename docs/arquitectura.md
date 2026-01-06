# Arquitectura de LicitaRadar 2.0

LicitaRadar 2.0 se ha diseñado con una arquitectura modular para facilitar su mantenimiento y escalabilidad.

## Módulos Principales

### 1. Core (`licitaradar/core.py`)

El cerebro de la operación. Orquesta el flujo:

1. Llama a `fetcher` para obtener datos.
2. Consulta `database` para filtrar duplicados.
3. Usa `filter` para detectar keywords relevantes.
4. Llama a `notifier` para enviar alertas.

### 2. Fetcher (`licitaradar/fetcher.py`)

Encargado de la comunicación externa:

- Parsea el feed ATOM de la PLACSP.
- (Opcional) Descarga el HTML de detalle de cada licitación.

### 3. Filter (`licitaradar/filter.py`)

Contiene la lógica de negocio para determinar qué es relevante.

- Normaliza texto (quita acentos, minúsculas).
- Busca coincidencias en listas de `WEB_KEYWORDS` y `EXTRA_KEYWORDS` (definidas en `config.py`).

### 4. Database (`licitaradar/database.py`)

Maneja la persistencia ligera mediante SQLite (`seen.sqlite3`).

- Almacena IDs (URLs) de licitaciones ya procesadas para evitar duplicados.

### 5. Notifier (`licitaradar/notifier.py`)

Genera y envía correos electrónicos.

- Construye mensajes MIME (Texto + HTML).
- Gestiona la conexión SMTP SSL.

## Flujo de Datos

`Internet (Feed)` -> `Fetcher` -> `Core` -> `Filter` -> `(Si Match)` -> `Notifier` -> `Email`
                                     ^
                                     |
                                 `Database` (Check seen)
