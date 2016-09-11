import asyncio
import aiohttp


class HTTPClient:
    """
    Client for interacting with HTTP
    """
    def __init__(self, bot, session):
        self.bot = bot
        self.session = session

    async def get(self, url, json=True):
        """
        Make a GET request

        Params
        ------
        url : str
            The URL to make the request to
        json : bool
            Whether to return the result as JSON (default: True)
        """
        async with self.session.get(url) as r:
            self.bot.log.debug("Made GET request to '{}' with response code {}".format(url, r.status))
            if json:
                return await r.json()
            else:
                return await r.text()
