# Configuration

The client reads `wowchat.toml` from the project root. The setup wizard (`python src/configure.py`) writes it for you; this page describes every option for manual editing. A complete example is in `wowchat.example.toml`.

## Environment variables

Sensitive values can be kept out of the file. When set, these variables replace the matching option:

| Variable | Replaces |
| --- | --- |
| `DISCORD_TOKEN` | `discord.token` |
| `WOW_ACCOUNT` | `wow.account` |
| `WOW_PASSWORD` | `wow.password` |
| `WOW_CHARACTER` | `wow.character` |

## `[discord]`

| Option | Required | Description |
| --- | --- | --- |
| `token` | Yes | Bot token from the Discord developer portal. |
| `bot_system_channel` | No | Channel for connection notices, the server MOTD and guild events without their own channel. |
| `enable_dot_commands` | No | Allow `.who`, `.gmotd` and `.r` from Discord. Defaults to `true`. |
| `item_database` | No | Base URL used to turn WoW item links into clickable links. |
| `gm_icon` | No | Emoji prefixed to messages sent by GMs, such as `<:GMIcon:123456789>`. |
| `dot_commands_whitelist` | No | Reserved. Read from the file but not applied by the current version. |
| `enable_commands_channels` | No | Reserved. Read from the file but not applied by the current version. |
| `enable_tag_failed_notifications` | No | Reserved. Read from the file but not applied by the current version. |

### `[discord.raid_icons]`

Replaces the eight raid target markers with Discord emojis. Keys `1` to `8` follow the in-game order (star, circle, diamond, triangle, moon, square, cross, skull).

```toml
[discord.raid_icons]
enabled = true
1 = "<:RaidStar:123456789>"
8 = "<:RaidSkull:123456789>"
```

## `[wow]`

| Option | Required | Description |
| --- | --- | --- |
| `realmlist` | Yes | Logon server as `host:port`. The port defaults to `3724`. |
| `realm` | Yes | Realm name exactly as shown in the realm list. |
| `account` | Yes | Account name. |
| `password` | Yes | Account password. |
| `character` | Yes | Character that logs in. |
| `version` | No | Game version. Defaults to `1.12.1`. |
| `locale` | No | Client locale, such as `enUS` or `esES`. Defaults to `enUS`. |
| `platform` | No | `Mac` or `Windows`. Defaults to `Mac`, which avoids Warden checks on most servers. |
| `enable_server_motd` | No | Post the server message of the day. Defaults to `true`. |
| `realm_build` / `game_build` / `build` | No | Override the build number derived from `version`. |

Supported versions:

| Expansion | Versions |
| --- | --- |
| Vanilla | `1.6.1`, `1.6.2`, `1.6.3`, `1.7.1`, `1.8.4`, `1.9.4`, `1.10.2`, `1.11.2`, `1.12.1`, `1.12.2`, `1.12.3` |
| The Burning Crusade | `2.4.3` |
| Wrath of the Lich King | `3.2.2`, `3.3.0`, `3.3.2`, `3.3.3`, `3.3.5` |
| Cataclysm | `4.3.4` |
| Mists of Pandaria | `5.4.8` |

## `[[chat.channels]]`

Each entry links one WoW chat to one Discord channel. Repeat the block for every relay.

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

| Option | Description |
| --- | --- |
| `direction` | `both`, `wow_to_discord` or `discord_to_wow`. |
| `wow.type` | `Guild`, `Officer`, `Say`, `Yell`, `Emote`, `Whisper`, `Party`, `Raid`, `Battleground`, `System` or `Channel`. |
| `wow.channel` | Custom channel name, only for `type = "Channel"`. |
| `wow.format` | Format of messages sent from Discord to WoW. Placeholder: `%message`. |
| `discord.channel` | Discord channel name, without `#`. |
| `discord.format` | Format of messages sent from WoW to Discord. Placeholders: `%user`, `%message`, `%target` (custom channel name). |
| `wow.filters` / `discord.filters` | Optional filters for this relay, with the same keys as `[filters]`. |

## `[guild.<event>]`

Events: `online`, `offline`, `joined`, `left`, `removed`, `promoted`, `demoted`, `motd`, `achievement`.

| Option | Description |
| --- | --- |
| `enabled` | Post this event. `online` and `offline` are disabled by default. |
| `format` | Message format. Placeholders: `%user`, `%target`, `%rank`, `%message`, `%achievement`. |
| `channel` | Discord channel for this event. Defaults to `bot_system_channel`. |

## `[filters]`

Drops WoW messages that match any regular expression, for every relay.

| Option | Description |
| --- | --- |
| `enabled` | Turn the filters on. |
| `patterns` | List of regular expressions. |

## `[gm_commands]`

Lets members with an allowed role run server commands by writing them in a Discord channel. The character needs GM rights on the server.

| Option | Description |
| --- | --- |
| `enabled` | Turn the feature on. Defaults to `false`. |
| `channel` | Discord channel where commands are written. |
| `allowed_roles` | List of Discord role IDs allowed to run commands. |
| `mode` | `auto` detects the server core; `azeroth` and `trinity` force a core; `chat` sends commands as chat messages. |
| `timeout` | Seconds to wait for the server reply. Defaults to `5.0`. |
| `blocked_commands` | Commands that are always rejected, such as `server shutdown`. |
