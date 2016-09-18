import aiohttp
import asyncio

from turbo.utils import Logging
from turbo.req import HTTPClient

loop = asyncio.get_event_loop()
assert loop


class FakeBot():
    def __init__(self, loop):
        self.logger = Logging('turbo.log')
        self.log = self.logger.lg
        self.session = aiohttp.ClientSession(loop=loop)

    async def get_test(self, client):
        req = await client.get('https://www.google.co.uk/', json=False)
        assert req

bot = FakeBot(loop)
assert bot
assert bot.logger
assert bot.log
assert bot.session

http = HTTPClient(bot, bot.session)
assert http

loop.run_until_complete(bot.get_test(http))
loop.close
