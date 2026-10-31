# Configuración

El cliente lee `wowchat.toml` desde la raíz del proyecto. El asistente (`python src/configure.py`) lo escribe por ti; esta página describe cada opción para editarlo a mano. Hay un ejemplo completo en `wowchat.example.toml`.

## Variables de entorno

Los valores sensibles pueden quedar fuera del archivo. Si están definidas, estas variables reemplazan la opción correspondiente:

| Variable | Reemplaza |
| --- | --- |
| `DISCORD_TOKEN` | `discord.token` |
| `WOW_ACCOUNT` | `wow.account` |
| `WOW_PASSWORD` | `wow.password` |
| `WOW_CHARACTER` | `wow.character` |

## `[discord]`

| Opción | Obligatoria | Descripción |
| --- | --- | --- |
| `token` | Sí | Token del bot del portal de desarrolladores de Discord. |
| `bot_system_channel` | No | Canal para avisos de conexión, el MOTD del servidor y los eventos de hermandad sin canal propio. |
| `enable_dot_commands` | No | Permite `.who`, `.gmotd` y `.r` desde Discord. Por defecto `true`. |
| `item_database` | No | URL base para convertir los enlaces de objetos de WoW en enlaces clicables. |
| `gm_icon` | No | Emoji antepuesto a los mensajes de GMs, por ejemplo `<:GMIcon:123456789>`. |
| `dot_commands_whitelist` | No | Reservada. Se lee del archivo pero la versión actual no la aplica. |
| `enable_commands_channels` | No | Reservada. Se lee del archivo pero la versión actual no la aplica. |
| `enable_tag_failed_notifications` | No | Reservada. Se lee del archivo pero la versión actual no la aplica. |

### `[discord.raid_icons]`

Reemplaza las ocho marcas de banda por emojis de Discord. Las claves `1` a `8` siguen el orden del juego (estrella, círculo, rombo, triángulo, luna, cuadrado, cruz, calavera).

```toml
[discord.raid_icons]
enabled = true
1 = "<:RaidStar:123456789>"
8 = "<:RaidSkull:123456789>"
```

## `[wow]`

| Opción | Obligatoria | Descripción |
| --- | --- | --- |
| `realmlist` | Sí | Servidor de logon como `host:puerto`. El puerto por defecto es `3724`. |
| `realm` | Sí | Nombre del reino tal como aparece en la lista de reinos. |
| `account` | Sí | Nombre de la cuenta. |
| `password` | Sí | Contraseña de la cuenta. |
| `character` | Sí | Personaje que inicia sesión. |
| `version` | No | Versión del juego. Por defecto `1.12.1`. |
| `locale` | No | Idioma del cliente, como `enUS` o `esES`. Por defecto `enUS`. |
| `platform` | No | `Mac` o `Windows`. Por defecto `Mac`, que evita las comprobaciones de Warden en la mayoría de servidores. |
| `enable_server_motd` | No | Publica el mensaje del día del servidor. Por defecto `true`. |
| `realm_build` / `game_build` / `build` | No | Sobrescribe el número de build derivado de `version`. |

Versiones soportadas:

| Expansión | Versiones |
| --- | --- |
| Vanilla | `1.6.1`, `1.6.2`, `1.6.3`, `1.7.1`, `1.8.4`, `1.9.4`, `1.10.2`, `1.11.2`, `1.12.1`, `1.12.2`, `1.12.3` |
| The Burning Crusade | `2.4.3` |
| Wrath of the Lich King | `3.2.2`, `3.3.0`, `3.3.2`, `3.3.3`, `3.3.5` |
| Cataclysm | `4.3.4` |
| Mists of Pandaria | `5.4.8` |

## `[[chat.channels]]`

Cada entrada enlaza un chat de WoW con un canal de Discord. Repite el bloque por cada relay.

```toml
[[chat.channels]]
direction = "both"

[chat.channels.wow]
type = "Channel"
channel = "world"
format = "%message"

[chat.channels.discord]
channel = "world-chat"
format = "[%target] [%user]: %message"
```

| Opción | Descripción |
| --- | --- |
| `direction` | `both`, `wow_to_discord` o `discord_to_wow`. |
| `wow.type` | `Guild`, `Officer`, `Say`, `Yell`, `Emote`, `Whisper`, `Party`, `Raid`, `Battleground`, `System` o `Channel`. |
| `wow.channel` | Nombre del canal personalizado, solo con `type = "Channel"`. |
| `wow.format` | Formato de los mensajes de Discord a WoW. Marcador: `%message`. |
| `discord.channel` | Nombre del canal de Discord, sin `#`. |
| `discord.format` | Formato de los mensajes de WoW a Discord. Marcadores: `%user`, `%message`, `%target` (nombre del canal personalizado). |
| `wow.filters` / `discord.filters` | Filtros opcionales de este relay, con las mismas claves que `[filters]`. |

## `[guild.<evento>]`

Eventos: `online`, `offline`, `joined`, `left`, `removed`, `promoted`, `demoted`, `motd`, `achievement`.

| Opción | Descripción |
| --- | --- |
| `enabled` | Publica este evento. `online` y `offline` están desactivados por defecto. |
| `format` | Formato del mensaje. Marcadores: `%user`, `%target`, `%rank`, `%message`, `%achievement`. |
| `channel` | Canal de Discord para este evento. Por defecto `bot_system_channel`. |

## `[filters]`

Descarta los mensajes de WoW que coincidan con alguna expresión regular, en todos los relays.

| Opción | Descripción |
| --- | --- |
| `enabled` | Activa los filtros. |
| `patterns` | Lista de expresiones regulares. |

## `[gm_commands]`

Permite a los miembros con un rol autorizado ejecutar comandos del servidor escribiéndolos en un canal de Discord. El personaje necesita permisos de GM en el servidor.

| Opción | Descripción |
| --- | --- |
| `enabled` | Activa la funcionalidad. Por defecto `false`. |
| `channel` | Canal de Discord donde se escriben los comandos. |
| `allowed_roles` | Lista de IDs de roles de Discord autorizados. |
| `mode` | `auto` detecta el core del servidor; `azeroth` y `trinity` fuerzan un core; `chat` envía los comandos como mensajes de chat. |
| `timeout` | Segundos de espera de la respuesta del servidor. Por defecto `5.0`. |
| `blocked_commands` | Comandos que siempre se rechazan, como `server shutdown`. |
