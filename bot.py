import logging
import sys
import colorlog
import os

from discord.ext import commands
from tsrc.config import Config
from tsrc.exceptions import Shutdown

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


initial_extensions = [
    'cogs.repl'
]

################################################################################


class Turbo(commands.Bot):
    def __init__(self):
        self.config = Config('config/config.ini')
        log.debug('Initialising commands.Bot')
        super().__init__(command_prefix=self.config.prefix, description=self.config.description, self_bot=True)

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception as e:
                log.error('Failed to load extension {}\n{}: {}'.format(extension, type(e).__name__, e))

    async def on_ready(self):
        log.info("Logged into Discord as: {}".format(self.user))


if __name__ == '__main__':
    try:
        bot = Turbo()
        bot.run(bot.config.token, bot=False)
    except Shutdown:
        os._exit(1)
