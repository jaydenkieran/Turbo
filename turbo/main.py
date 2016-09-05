import discord
import aiohttp

from .utils import Logging, Config

class Turbo(discord.Client):
    def __init__(self):
        self.logger = Logging('turbo.log')
        self.log = self.logger.lg
        self.config = Config('config/turbo.ini')

        super().__init__()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.log.debug('Created aiohttp client session')

    async def on_ready(self):
        self.log.info('Logged in as {0} ({0.id})'.format(self.user))

if __name__ == "__main__":
    bot = Turbo()
    bot.run(bot.config.token)
