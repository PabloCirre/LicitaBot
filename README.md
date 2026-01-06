# 🛰️ LicitaRadar 2.0

### Radar Automatizado de Licitaciones Públicas

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

*Detecta, Filtra y Notifica oportunidades de negocio Web en tiempo real.*

[Comenzar](#-comenzando) • [Características](#-características) • [Configuración](#-configuración) • [Documentación](#-documentación)

</div>

---

## 🚀 ¿Qué es LicitaRadar 2.0?

LicitaRadar 2.0 es un agente inteligente diseñado para monitorizar la Plataforma de Contratación del Sector Público (PLACSP). Su misión es **ahorrarte tiempo**: escanea miles de licitaciones, filtra el ruido y te avisa solo cuando encuentra contratos relacionados con **Desarrollo Web, Tecnología y Transformación Digital**.

## ✨ Características

- 📡 **Monitorización 24/7**: Escucha activa del feed de licitaciones.
- 🧠 **Filtrado Inteligente**: Detección de keywords relevantes (Web, Ecommerce, Plataformas).
- 📧 **Alertas Inmediatas**: Notificaciones por email con 'Personalidad BipBip' y datos clave.
- 💾 **Memoria Persistente**: Base de datos SQLite para evitar duplicados.
- 🐳 **Modo Demonio**: Ejecución continua automática.

## 🛠 Comenzando

### Prerrequisitos

- Python 3.8+
- Acceso a un servidor SMTP (Gmail, Outlook, o propio)

### Instalación Rápida

1. **Clona el repositorio**

    ```bash
    git clone https://github.com/tu-usuario/licitaradar.git
    cd licitaradar
    ```

2. **Instala dependencias**

    ```bash
    pip install -r requirements.txt
    ```

3. **Configura tu entorno**
    Copia el archivo de ejemplo y edítalo:

    ```bash
    # En Windows
    copy config\.env.example .env
    ```

4. **¡Despega! 🚀**

    ```bash
    python -m licitaradar
    ```

## ⚙️ Configuración

LicitaRadar 2.0 usa variables de entorno para mantener tus secretos a salvo. Nunca subas tus contraseñas al repositorio.

| Variable | Descripción |
|----------|-------------|
| `SMTP_HOST` | Host de tu servidor de correo |
| `SMTP_PASS` | Tu contraseña de aplicación |
| `MAIL_TO` | Email donde recibirás las alertas |

*Ver `docs/manual_usuario.md` para más detalles.*

## 📚 Documentación

Hemos preparado documentación detallada para ti:

- [📖 Manual de Usuario](docs/manual_usuario.md)
- [🏗 Arquitectura del Sistema](docs/arquitectura.md)

## 🤝 Contribuir

Las Pull Requests son bienvenidas. Para cambios mayores, por favor abre primero un issue.

---
<div align="center">
Hecho con kbrd por el equipo de Desarrollo
</div>
