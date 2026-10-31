# Getting started

This guide creates the Discord bot, installs the client, writes its configuration and starts it.

## Prerequisites

| Tool | Version | Used for |
| --- | --- | --- |
| Python | 3.12+ | Running the client and the setup wizard |
| Git | 2.40+ | Cloning the repository |
| A modern browser | Any | Web setup mode only |

You also need a WoW account and character on the target server. Use an account dedicated to the bot: the character stays online while the client runs.

## Create the Discord bot

1. Open the [Discord developer portal](https://discord.com/developers/applications) and create an application.
2. In **Bot**, reset the token and copy it. You will paste it in the setup wizard.
3. In the same page, enable **Message Content Intent**. It is the only privileged intent the client uses.
4. In **OAuth2 > URL Generator**, select the `bot` scope and the permissions *View Channels*, *Send Messages*, *Embed Links* and *Read Message History*. Open the generated URL to invite the bot.
5. Create the Discord channels you want to relay, for example `guild-chat`, `officer-chat` and `bot-system`.

To restrict GM commands by role, enable **Developer Mode** in Discord (User Settings > Advanced), right click a role and choose **Copy Role ID**.

## Install

1. Clone the repository and enter it:

   ```bash
   git clone https://github.com/Zerik-Official/WowMiniClient
   cd WowMiniClient
   ```

2. Create a virtual environment and install the dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

   On Windows PowerShell, activate it with `venv\Scripts\Activate.ps1`.

## Configure

Run the setup wizard from the project root:

```bash
python src/configure.py
```

It asks how you want to configure the client:

| Mode | How it works |
| --- | --- |
| In the browser | Starts a temporary server on `127.0.0.1` with a random port and opens the setup page. The URL carries a random key, so other pages cannot write your configuration. Press **Save configuration**, then **Close setup** to stop the server. |
| In the console | Asks every setting in the terminal with selectable lists and checkboxes. Good for servers without a desktop. |

Both modes write `wowchat.toml` in the project root, validate it with the same parser the client uses and keep any section they do not manage. Running the wizard again loads the current values, so it can also be used to edit the configuration. Secrets left empty in console mode keep their current value.

Options:

| Option | Description |
| --- | --- |
| `--mode console` / `--mode web` | Skip the mode question |
| `--config PATH` | Write to another file instead of `wowchat.toml` |
| `--no-browser` | Print the web setup URL without opening the browser |

You can also copy `wowchat.example.toml` to `wowchat.toml` and edit it by hand. Every option is described in [Configuration](configuration.md).

## Run

```bash
python src/main.py
```

The client logs into the realm, enters the world with the character and connects the Discord bot. Both connections reconnect automatically when they drop. Stop it with `Ctrl+C`.

## Tests

Install the development tools and run the test suite:

```bash
pip install -e ".[dev]"
pytest
```
