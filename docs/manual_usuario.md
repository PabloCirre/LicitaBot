# Manual de Usuario - LicitaRadar 2.0

## 1. Introducción

LicitaRadar 2.0 es un "radar" automatizado que monitoriza el feed de licitaciones de la Plataforma de Contratación del Sector Público (PLACSP), específicamente la sindicación 643. Su objetivo es detectar licitaciones relacionadas con desarrollo web y tecnología, y notificar por correo electrónico.

## 2. Requisitos Previos

- Python 3.8 o superior.
- Conexión a Internet.
- Un servidor SMTP para envío de correos.

## 3. Instalación

1. Clona el repositorio.
2. Instala las dependencias:

    ```bash
    pip install -r requirements.txt
    ```

## 4. Configuración

Crea tus variables de entorno. Puedes basarte en `config/.env.example`:

- `SMTP_HOST`: Servidor de correo (ej. smtp.gmail.com).
- `SMTP_PASS`: Contraseña de aplicación.
- `MAIL_TO`: Quién recibe las alertas.

## 5. Uso

### Ejecución normal (una pasada)

```bash
python -m licitaradar
```

### Modo servicio (demonio)

Ejecuta cada hora indefinidamente:

```bash
python -m licitaradar --daemon
```

### Opciones adicionales

Ver ayuda:

```bash
python -m licitaradar --help
```
