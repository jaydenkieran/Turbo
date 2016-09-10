import discord
import aiohttp
import inspect
import asyncio

from .utils import Logging, Config
from .commands import Commands, Response
from .exceptions import InvalidUsage
from .constants import VERSION


class Turbo(discord.Client):

    def __init__(self):
        self.logger = Logging('turbo.log')
        self.log = self.logger.lg
        self.config = Config('config/turbo.ini')

        super().__init__()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.log.debug('Created aiohttp client session')
        self.commands = Commands(self)

        self.log.info("Turbo ({}). Connecting...".format(VERSION))

    def run(self, token):
        """
        Override's discord.py's function for running the bot
        """
        try:
            super().run(token, bot=(not self.config.selfbot))
        except discord.LoginFailure:
            self.log.critical("Incorrect login token")
            if not self.config.selfbot:
                self.log.critical(
                    "Using your own token? Change 'selfbot' to 'True' in the config")
            else:
                self.log.critical(
                    "Using an OAuth account? Change 'selfbot' to 'False' in the config")
        except discord.HTTPException as e:
            self.log.critical(e)

    def format_bool(self, boolean):
        """
        Returns a string based on bool value
        """
        return ['no', 'yes'][boolean]

    async def send_message(self, dest, content, *, tts=False, delete=0):
        """
        Overrides discord.py's function for sending a message
        """
        msg = None
        try:
            msg = await super().send_message(dest, content, tts=tts)
            self.log.debug(
                'Sent message ID {} in #{}'.format(msg.id, dest.name))

            if msg and delete and self.config.delete:
                asyncio.ensure_future(self._delete_after(msg, delete))
        except discord.Forbidden:
            self.log.warning(
                "No permission to send a message to #{}".format(dest.name))
        except discord.NotFound:
            self.log.warning(
                "Could not find channel #{} to send a message to".format(dest.name))
        except discord.HTTPException as e:
            self.log.warning(
                "Problem sending a message in #{}: {}".format(dest.name, e))
        return msg

    async def delete_message(self, msg):
        """
        Overrides discord.py's function for deleting a message
        """
        try:
            await super().delete_message(msg)
            self.log.debug(
                'Deleted message ID {} in #{}'.format(msg.id, msg.channel.name))
        except discord.Forbidden:
            self.log.warning(
                "No permission to delete a message in #{}".format(msg.channel.name))
        except discord.HTTPException as e:
            self.log.warning(
                "Problem deleting a message in #{}: {}".format(msg.channel.name, e))

    async def _delete_after(self, msg, time):
        """
        Deletes a message after a given amount of time
        """
        self.log.debug("Scheduled message ID {} to delete ({}s)".format(msg.id, time))
        await asyncio.sleep(time)
        await self.delete_message(msg)

    async def on_ready(self):
        self.log.info('Logged in as {0} ({0.id})'.format(self.user))
        print(flush=True)
        self.log.info('Configuration:')
        self.log.info('- Selfbot: ' + self.format_bool(self.config.selfbot))
        self.log.info('- Allow PMs: ' + self.format_bool(self.config.pm))
        self.log.info('- Prefix: ' + self.config.prefix)
        print(flush=True)

    async def on_message(self, message):
        await self.wait_until_ready()
        content = message.content.strip()
        if not self.config.pm and message.channel.is_private:
            return
        if not content.startswith(self.config.prefix):
            return
        if (message.author != self.user) and self.config.selfbot:
            return
        cmd, *args = content.split()
        cmd = cmd[len(self.config.prefix):].lower().strip()
        h = getattr(self.commands, 'c_%s' % cmd, None)
        if not h:
            return

        if not message.channel.is_private:
            self.log.info(
                "[Command] {0} [{1.server} | #{1}] - {2}".format(message.author, message.channel, content))
        else:
            self.log.info(
                "[Command] {0} [Private Message | {1}] - {2}".format(message.author, message.channel, content))

        s = inspect.signature(h)
        p = s.parameters.copy()
        kw = {}
        if p.pop('message', None):
            kw['message'] = message
        if p.pop('channel', None):
            kw['channel'] = message.channel
        if p.pop('author', None):
            kw['author'] = message.author
        if p.pop('server', None):
            kw['server'] = message.server
        if p.pop('args', None):
            kw['args'] = args

        ae = []
        for key, param in list(p.items()):
            doc_key = '[%s=%s]' % (
                key, param.default) if param.default is not inspect.Parameter.empty else key
            ae.append(doc_key)
            if not args and param.default is not inspect.Parameter.empty:
                p.pop(key)
                continue
            if args:
                v = args.pop(0)
                kw[key] = v
                p.pop(key)

        try:
            if p:
                raise InvalidUsage()

            r = await h(**kw)
            if r and isinstance(r, Response):
                content = r.content
                if r.reply and not self.config.selfbot:
                    content = "{}: {}".format(message.author.mention, content)
                await self.send_message(message.channel, content, delete=r.delete)
        except InvalidUsage:
            docs = getattr(h, '__doc__', None)
            docs = '\n'.join(l.strip() for l in docs.split('\n'))
            return await self.send_message(message.channel, ":warning: Incorrect usage.\n```\n{}\n```".format(
                docs.format(prefix=self.config.prefix)))

if __name__ == "__main__":
    bot = Turbo()
    bot.run(bot.config.token)
