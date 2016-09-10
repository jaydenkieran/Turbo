# :rocket: Turbo (2.0)
Turbo is a Discord bot that does some weird and wacky things. It can function as a normal bot or a selfbot. With fun commands and utility commands suitable for server administrators and general users alike, Turbo is a general purpose bot designed for just about any situation.

## Requirements
This bot is coded in **Python**, so that is required to run it. As well as that, there are some additional Python dependencies that should be installed using `pip install -U -r requirements.txt`

- `discord.py`
- `aiohttp`
- `colorlog`

## Installing
### Windows
1. Install [Git for Windows](https://git-for-windows.github.io/)
2. Open Git Bash (right-click in a folder, select `Git Bash` or `Git Bash Here`)
3. Run `git clone https://github.com/jaydenkieran/Turbo.git -b master`

### Linux
1. Install Git using `sudo apt-get install git` (`apt-get` may be substituted for a different package manager on your system)
2. Run `git clone https://github.com/jaydenkieran/Turbo.git -b master`

### Mac
1. Install Git using Homebrew: `brew install git`
2. Run `git clone https://github.com/jaydenkieran/Turbo.git -b master` in Terminal

## Configuration
Open `config/turbo.example.ini` and edit it. Save it in the `config` folder as `turbo.ini`.

## Running
### Windows
Open `runbot.bat`. **If you are using Git Bash**, you should run the bot using the command `winpty runbot.bat` instead to avoid unicode issues.
### Other platforms
Run `python run.py`.

## Commands
You can change the default **command prefix** in `config/turbo.ini`

- `~ping` - Test the bot's latency
- `~shutdown <normal/n/hard/h>` - Shuts the bot down
- `~help [command]` - Provides a list of commands, or docs for a command
- `~eval <code>` - Evaluates Python code
- `~snowflake [id/@user/#channel/emote/@role]` - Gets the creation time of a Discord snowflake ID
- `~status [status]` - Changes/clears status
- `~discrim [discrim]` - Gets matching visible users with discriminator
