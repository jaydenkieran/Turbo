import logging
import sys
import colorlog
import os
import discord

from discord.ext import commands
from tsrc.config import Config
from tsrc.exceptions import Shutdown
from tsrc.utils import get_destination_string, format_bool, format_option
from tsrc.constants import BOT_VERSION

# Setup logging
log = logging.getLogger('turbo')
log.setLevel(logging.DEBUG)
fh = logging.FileHandler(filename='turbo.log', encoding='utf-8', mode='w')
fh.setFormatter(logging.Formatter(
    "[{asctime}] {levelname} ({filename} L{lineno}, {funcName}): {message}", style='{'
))
log.addHandler(fh)
sh = logging.StreamHandler(stream=sys.stdout)
sh.setFormatter(colorlog.LevelFormatter(
    fmt={
        "DEBUG": "{log_color}{levelname} ({module} L{lineno}, {funcName}): {message}",
        "INFO": "{log_color}{message}",
        "WARNING": "{log_color}{levelname}: {message}",
        "ERROR": "{log_color}{levelname} ({module} L{lineno}, {funcName}): {message}",
        "CRITICAL": "{log_color}{levelname} ({module} L{lineno}, {funcName}): {message}"
    },
    log_colors={
        "DEBUG": "purple",
        "INFO": "white",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red"
    },
    style='{'
))
sh.setLevel(logging.DEBUG)
log.addHandler(sh)

################################################################################

initial_extensions = [
    'cogs.admin',
    'cogs.core'
]

################################################################################


class Turbo(commands.Bot):
    def __init__(self):
        self._version = BOT_VERSION

        self.config = Config('config/config.ini')
        log.debug('Initialising commands.Bot')
        super().__init__(command_prefix=self.config.prefix, description=self.config.description, self_bot=True)

        # default help command is cancer
        self.remove_command('help')
        log.debug('Removed default help command')

        # load extensions
        for extension in initial_extensions:
            try:
                self.load_extension(extension)
                log.debug('Loaded extension: {}'.format(extension))
            except Exception as e:
                log.error('Failed to load extension {}\n{}: {}'.format(extension, type(e).__name__, e))

    async def on_ready(self):
        log.info("Logged into Discord as: {0} ({0.id})".format(self.user))
        print()
        print("-----\nConfiguration\n-----")
        print(format_option('Prefix: ', self.config.prefix))
        print()

    async def on_command(self, command, ctx):
        msg = ctx.message
        d = get_destination_string(msg)
        log.info('{0.timestamp}: {0.author.name} in {1}: {0.content}'.format(msg, d))

    async def on_command_error(self, exception, context):
        exc_type = type(exception)
        if exc_type is discord.ext.commands.errors.CommandNotFound:
            return
        elif exc_type is discord.ext.commands.errors.MissingRequiredArgument:
            await self.edit(context.message, 'Missing argument(s).')
        else:
            await super().on_command_error(exception, context)

    async def edit(self, msg, *args, **kwargs):
        """Edit a message. Wrapper function."""
        d = get_destination_string(msg)
        log.debug('Editing {0.id} by {0.author.name} in {1}'.format(msg, d))
        try:
            await super().edit_message(msg, *args, **kwargs)
        except discord.HTTPException as e:
            log.error("Editing failed ({}): {}".format(msg.id, e))

################################################################################

if __name__ == '__main__':
    try:
        bot = Turbo()
        bot.run(bot.config.token, bot=False)
    except Shutdown:
        os._exit(1)
