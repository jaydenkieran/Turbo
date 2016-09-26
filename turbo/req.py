class HTTPClient:

    """
    Client for interacting with HTTP
    """

    def __init__(self, bot, session):
        self.bot = bot
        self.session = session

    async def get(self, url, json=True, headers=None):
        """
        Make a GET request

        Params
        ------
        url : str
            The URL to make the request to
        json : bool
            Whether to return the result as JSON (default: True)
        headers : dict
            Additional headers to send with the request
        """
        async with self.session.get(url, headers=headers) as r:
            self.bot.log.debug(
                "Made GET request to '{}' with response code {}".format(url, r.status))
            if json:
                return await r.json()
            else:
                return await r.text()
