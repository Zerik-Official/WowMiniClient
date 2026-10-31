<h1 align="center">
  WowMiniClient
</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-111111?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/discord.py-111111?style=for-the-badge&logo=discord">
  <img src="https://img.shields.io/badge/asyncio-111111?style=for-the-badge&logo=python">
  <img src="https://img.shields.io/badge/Flask-111111?style=for-the-badge&logo=flask">
  <img src="https://img.shields.io/badge/Jinja2-111111?style=for-the-badge&logo=jinja">
  <img src="https://img.shields.io/badge/Tailwind_CSS-111111?style=for-the-badge&logo=tailwindcss">
  <img src="https://img.shields.io/badge/Font_Awesome-111111?style=for-the-badge&logo=fontawesome">
  <img src="https://img.shields.io/badge/InquirerPy-111111?style=for-the-badge&logo=gnubash&logoColor=white">
  <img src="https://img.shields.io/badge/TOML-111111?style=for-the-badge&logo=toml">
  <img src="https://img.shields.io/badge/Pytest-111111?style=for-the-badge&logo=pytest">
</p>

<p align="center">
  <img src=".github/preview.png" alt="Vista previa de WowMiniClient"/>
</p>

<p align="center">
  <strong>Español</strong> | <a href="./README.md">English</a>
</p>

WowMiniClient es un cliente ligero y sin interfaz gráfica de World of Warcraft escrito en Python. Conecta un personaje a un servidor privado sin el cliente del juego y retransmite el chat entre WoW y Discord: hermandad, oficiales, susurros, canales personalizados y más, además de eventos de hermandad, comandos con punto y comandos de GM ejecutados desde un canal de Discord.

## Funcionalidades

| Funcionalidad | Descripción |
| --- | --- |
| Retransmisión de chat | Relay en ambos sentidos entre chats de WoW (hermandad, oficiales, decir, gritar, susurros, grupo, banda, canales personalizados...) y canales de Discord, con formatos y filtros regex propios |
| Eventos de hermandad | Conexiones, desconexiones, ingresos, salidas, expulsiones, ascensos, descensos, MOTD y logros publicados en Discord |
| Comandos con punto | `.who`, `.gmotd` y `.r` (responder susurro) desde Discord |
| Comandos de GM | Ejecuta comandos del servidor desde un canal de Discord restringido por rol, con lista de bloqueo |
| Varias expansiones | Vanilla (1.6 a 1.12), TBC 2.4.3, WotLK 3.3.x, Cataclysm 4.3.4 y MoP 5.4.8 |
| Asistente de configuración | Consola (InquirerPy) o página web local temporal (Flask) para crear `wowchat.toml` |

Consulta la [documentación técnica](docs/README.md) para más detalles.

## Estructura del repositorio

```
WowMiniClient/
├── src/
│   ├── main.py                # Punto de entrada del cliente
│   ├── configure.py           # Punto de entrada del asistente
│   ├── configurator/          # Flujos de configuración por consola y web
│   ├── common/                # Lectura de config, tipos, enrutado
│   ├── crypto/                # SRP6, RC4 y cifrado de cabeceras
│   ├── realm/                 # Conexión al servidor de reinos (logon)
│   ├── game/                  # Conexión al servidor de juego y manejadores de paquetes
│   ├── warden/                # Manejo del anti-trampas Warden
│   ├── modules/bot/           # Bot de Discord
│   ├── utils/                 # Logger, banner y utilidades
│   └── data/                  # Nombres de zonas y logros
├── tests/
├── docs/
│   ├── en/                    # Documentación en inglés
│   └── es/                    # Documentación en español
├── wowchat.example.toml
├── pyproject.toml
└── requirements.txt
```

## Requisitos

- Python 3.12+
- Un bot de Discord con el intent Message Content activado
- Una cuenta y un personaje de WoW en el servidor de destino

## Primeros pasos

La [guía de primeros pasos](docs/es/getting-started.md) explica cómo crear el bot de Discord, cada opción de configuración y cómo ejecutar el cliente. Inicio rápido:

1. Crea un entorno virtual e instala las dependencias:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

   En Windows PowerShell, actívalo con `venv\Scripts\Activate.ps1`.

2. Ejecuta el asistente y elige consola o navegador:

   ```bash
   python src/configure.py
   ```

   Escribe `wowchat.toml` en la raíz del proyecto, que Git ignora. También puedes copiar `wowchat.example.toml` y editarlo a mano.

3. Inicia el cliente:

   ```bash
   python src/main.py
   ```

## Tests

```bash
pip install -e ".[dev]"
pytest
```
