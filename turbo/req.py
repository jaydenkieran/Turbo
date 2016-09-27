import aiohttp
import asyncio

from .constants import USER_AGENT


class HTTPClient:

    """
    Client for interacting with HTTP
    """

    def __init__(self, *, session=None, loop=asyncio.get_event_loop()):
        if session is None:
            self.session = aiohttp.ClientSession(loop=loop)
        else:
            self.session = session

        self.headers = {'User-Agent': USER_AGENT}

    async def request(self, method, url, **kwargs):
        """
        Makes a HTTP request
        DO NOT call this function yourself - use provided methods
        """
        async with self.session.request(method, url, **kwargs) as r:
            self.bot.log.debug("{0.method} [{0.url}] {0.status}/{0.reason}".format(r))
            if r.headers['Content-Type'] == 'application/json':
                return await r.json()
            else:
                return await r.text()

    async def get(self, url, *, headers={}, **kwargs):
        """
        Make a GET request

        Params
        ------
        url : str
            The URL to make the request to
        headers : dict
            Additional headers to send with the request

        Returns
        -------
        dict [or str]
            If result was not JSON, returns str
        """
        headers = {**self.headers, **headers}
        r = await self.request('GET', url, headers=headers, **kwargs)
        return r
