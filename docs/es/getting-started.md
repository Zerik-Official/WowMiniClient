# Primeros pasos

Esta guía crea el bot de Discord, instala el cliente, escribe su configuración y lo inicia.

## Requisitos previos

| Herramienta | Versión | Uso |
| --- | --- | --- |
| Python | 3.12+ | Ejecutar el cliente y el asistente de configuración |
| Git | 2.40+ | Clonar el repositorio |
| Un navegador moderno | Cualquiera | Solo para el modo de configuración web |

También necesitas una cuenta y un personaje de WoW en el servidor de destino. Usa una cuenta dedicada al bot: el personaje permanece conectado mientras el cliente está en ejecución.

## Crear el bot de Discord

1. Abre el [portal de desarrolladores de Discord](https://discord.com/developers/applications) y crea una aplicación.
2. En **Bot**, restablece el token y cópialo. Lo pegarás en el asistente de configuración.
3. En la misma página, activa **Message Content Intent**. Es el único intent privilegiado que usa el cliente.
4. En **OAuth2 > URL Generator**, selecciona el scope `bot` y los permisos *View Channels*, *Send Messages*, *Embed Links* y *Read Message History*. Abre la URL generada para invitar al bot.
5. Crea los canales de Discord que quieras retransmitir, por ejemplo `guild-chat`, `officer-chat` y `bot-system`.

Para restringir los comandos de GM por rol, activa el **Modo desarrollador** en Discord (Ajustes de usuario > Avanzado), haz clic derecho en un rol y elige **Copiar ID del rol**.

## Instalar

1. Clona el repositorio y entra en él:

   ```bash
   git clone https://github.com/Zerik-Official/WowMiniClient
   cd WowMiniClient
   ```

2. Crea un entorno virtual e instala las dependencias:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

   En Windows PowerShell, actívalo con `venv\Scripts\Activate.ps1`.

## Configurar

Ejecuta el asistente desde la raíz del proyecto:

```bash
python src/configure.py
```

Te pregunta cómo quieres configurar el cliente:

| Modo | Cómo funciona |
| --- | --- |
| En el navegador | Levanta un servidor temporal en `127.0.0.1` con un puerto aleatorio y abre la página de configuración. La URL lleva una clave aleatoria, así otras páginas no pueden escribir tu configuración. Pulsa **Save configuration** y después **Close setup** para detener el servidor. |
| En la consola | Pregunta cada opción en la terminal con listas seleccionables y casillas. Útil en servidores sin escritorio. |

Ambos modos escriben `wowchat.toml` en la raíz del proyecto, lo validan con el mismo parser que usa el cliente y conservan las secciones que no gestionan. Si vuelves a ejecutar el asistente, carga los valores actuales, así que también sirve para editar la configuración. En modo consola, los secretos que dejes vacíos mantienen su valor actual.

Opciones:

| Opción | Descripción |
| --- | --- |
| `--mode console` / `--mode web` | Omite la pregunta del modo |
| `--config RUTA` | Escribe en otro archivo en lugar de `wowchat.toml` |
| `--no-browser` | Muestra la URL de la configuración web sin abrir el navegador |

También puedes copiar `wowchat.example.toml` a `wowchat.toml` y editarlo a mano. Cada opción se describe en [Configuración](configuration.md).

## Ejecutar

```bash
python src/main.py
```

El cliente inicia sesión en el reino, entra al mundo con el personaje y conecta el bot de Discord. Ambas conexiones se reconectan solas si se caen. Detenlo con `Ctrl+C`.

## Tests

Instala las herramientas de desarrollo y ejecuta los tests:

```bash
pip install -e ".[dev]"
pytest
```
