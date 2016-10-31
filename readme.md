# :rocket: Turbo
Turbo is a Discord bot that does some weird and wacky things. It can function as a normal bot or a selfbot. With fun commands and utility commands suitable for server administrators and general users alike, Turbo is a general purpose bot designed for just about any situation.

## Requirements
This bot is coded in **Python**, so that is required to run it. As well as that, there are some additional Python dependencies that will be installed **automatically** when running your platform's specific scripts.

- `discord.py` (used for Discord integration)
- `aiohttp` (used for asynchronous web requests)
- `colorlog` (used for logging in console & file)
- `rethinkdb` (used for database storage, e.g tags)
- `beautifulsoup4` (used for parsing website HTML)
- `ruamel.yaml` (used for parsing YAML files)

## Installing
### Windows
1. Install [Git for Windows](https://git-for-windows.github.io/)
2. Open Git Bash (right-click in a folder, select `Git Bash` or `Git Bash Here`)
3. Run `git clone https://github.com/jaydenkieran/Turbo.git -b master`
4. Open `updatedeps-win.bat` in the new folder

### Linux
1. Install Git using `sudo apt-get install git` (`apt-get` may be substituted for a different package manager on your system)
2. Run `git clone https://github.com/jaydenkieran/Turbo.git -b master`
3. Run `updatedeps-linux.sh` in the new folder

### Mac
1. Install Git using Homebrew: `brew install git`
2. Run `git clone https://github.com/jaydenkieran/Turbo.git -b master` in Terminal
3. Run `updatedeps-mac.command` in the new folder

## Configuration
Open `config/turbo.example.ini` and edit it. Save it in the `config` folder as `turbo.ini`.

### Aliases
You can setup **aliases** for commands. To do so, copy `aliases.example.yml` to `aliases.yml`. In there, you can set aliases for different commands. The format in which you should do this is inside the example file. If you still need help, here's another example on how to set three different aliases for the `ping` command:

```yml
ping:
  - p
  - hello
  - test
```

If you enter an invalid command in the aliases file, the bot will inform you of this when you start it. It won't prevent the bot from starting if you have invalid commands in the file, those will just be ignored.

## Running
In order to use various commands, including commands relating to tags, you require a [RethinkDB database](https://www.rethinkdb.com/). Learn how to [install RethinkDB here](https://www.rethinkdb.com/docs/install/). If a database is unavailable, these commands will be disabled.

### Windows
Open `runbot-win.bat`. **If you are using Git Bash**, you should run the bot using the command `winpty runbot.bat` instead to avoid unicode issues.
### Linux
Run `runbot-linux.sh`.
### Mac
Run `runbot-mac.command`.

## Commands
The **command prefix** is set in the configuration file. By default, it is `~`. This prefix is needed before all commands.

Command | Usage | SB<sup>1</sup> | DB<sup>2</sup> | C<sup>3</sup>
--- | --- | --- | --- | ---
`ping` | Test the bot's connection to the Discord API |||
`stats` | Get statistics about servers, users, and the bot |||
`shutdown <normal/n/hard/h>` | Terminates the bot script |||
`help [command]` | Lists all commands. If a command is given, gives usage info |||
`eval <code>` | Allows you to execute Python code ||| Yes
`subprocess <command>` | Launch a subprocess ||| Yes
`snowflake [id/@user/#channel/emote/@role]` | Get the time created of a snowflake<sup>4</sup> |||
`status [status]` | Changes the user/bot's status, or clears it |||
`discrim [discrim]` | Return a list of visible users with matching discriminator |||
`changediscrim` | Change the user's discriminator | Yes ||
`tags` | Lists all tags || Yes |
`createtag <"name"> <"content">` | Adds a new tag with a given name and content || Yes |
`deletetag <"name">` | Deletes a tag || Yes |
`cleartags` | Deletes all tags || Yes |
`tag <name>` | Triggers a tag || Yes |
`cat` | Sends a random cat image |||
`youtube <query>` | Searches YouTube and returns results |||
`presence <online/idle/dnd/invisible>` | Changes presence status on Discord |||

- *<sup>1</sup>SB = Selfbot ONLY. The selfbot option must be enabled in the configuration file*
- *<sup>2</sup>DB = Database REQUIRED. A RethinkDB database connection must be available to use*
- *<sup>3</sup>C = Creator ONLY. Only the bot application creator can use this command (or the user if selfbot)*
- *<sup>4</sup>To learn more about snowflakes, read https://discordapp.com/developers/docs/reference#snowflake-id's*
