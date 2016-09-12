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
4. Open `updatedeps-win.bat` in the new folder

### Linux
1. Install Git using `sudo apt-get install git` (`apt-get` may be substituted for a different package manager on your system)
2. Run `git clone https://github.com/jaydenkieran/Turbo.git -b master`
3. Run `updatedeps-linux-mac.sh` in the new folder

### Mac
1. Install Git using Homebrew: `brew install git`
2. Run `git clone https://github.com/jaydenkieran/Turbo.git -b master` in Terminal
3. Run `updatedeps-linux-mac.sh` in the new folder

## Configuration
Open `config/turbo.example.ini` and edit it. Save it in the `config` folder as `turbo.ini`.

## Running
### Windows
Open `runbot-win.bat`. **If you are using Git Bash**, you should run the bot using the command `winpty runbot.bat` instead to avoid unicode issues.
### Other platforms
Run `runbot-linux-mac.sh`.

## Commands
The **command prefix** is set in the configuration file. By default, it is `~`.

Command | Usage | Requires selfbot
--- | --- | ---
`ping` | Test the bot's connection to the Discord API | :no_entry_sign:
`stats` | Get statistics about servers, users, and the bot | :no_entry_sign:
`shutdown <normal/n/hard/h>` | Terminates the bot script | :no_entry_sign:
`help [command]` | Lists all commands. If a command is given, gives usage info | :no_entry_sign:
`eval <code>` | Allows you to execute Python code | :no_entry_sign:
`snowflake [id/@user/#channel/emote/@role]` | Get the time created of a snowflake<sup>1</sup> | :no_entry_sign:
`status [status]` | Changes the user/bot's status, or clears it | :no_entry_sign:
`discrim [discrim]` | Return a list of visible users with matching discriminator | :no_entry_sign:
`changediscrimm` | Change the user's discriminator | :white_check_mark:
`tags` | Lists all tags | :no_entry_sign:
`addtag <"name"> <"content">` | Creates a new tag | :no_entry_sign:
`deletetag <"name">` | Deletes a tag | :no_entry_sign:
`cleartags` | Deletes all tags | :no_entry_sign:
`tag <name>` | Triggers a tag | :no_entry_sign:
`cat` | Sends a random cat image

*<sup>1</sup>To learn more about snowflakes, read https://discordapp.com/developers/docs/reference#snowflake-id's*
