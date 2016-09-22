import discord
import aiohttp
import inspect
import asyncio
import time
import sys
import traceback

from .utils import Logging, Config, Yaml
from .commands import Commands, Response
from .exceptions import InvalidUsage, Shutdown
from .constants import VERSION
from .database import Database
from .req import HTTPClient


class Turbo(discord.Client):

    def __init__(self):
        self.logger = Logging('turbo.log')
        self.log = self.logger.lg
        self.config = Config('config/turbo.ini')
        self.yaml = Yaml()

        super().__init__()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.log.debug('Created aiohttp client session')
        self.db = Database(self)
        self.req = HTTPClient(self, self.session)
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

    def get_uptime(self):
        """
        Returns the uptime of the bot
        """
        return time.time() - self.started

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

    async def edit_message(self, message, content, *, delete=0):
        """
        Overrides discord.py's function for editing a message
        """
        msg = None
        try:
            msg = await super().edit_message(message, content)
            self.log.debug(
                'Edited message ID {} in #{}'.format(msg.id, msg.channel))

            if msg and delete and self.config.delete:
                asyncio.ensure_future(self._delete_after(msg, delete))
        except discord.Forbidden:
            self.log.warning(
                "No permission to edit a message in #{}".format(message.channel))
        except discord.NotFound:
            self.log.warning(
                "Could not find message ID {} to edit".format(message.id))
        except discord.HTTPException as e:
            self.log.warning(
                "Problem editing a message in #{}: {}".format(message.channel, e))
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
        self.log.debug(
            "Scheduled message ID {} to delete ({}s)".format(msg.id, time))
        await asyncio.sleep(time)
        await self.delete_message(msg)

    async def on_ready(self):
        """
        Called when the bot is connected to Discord
        """
        self.started = time.time()
        self.log.info('Logged in as {0} ({0.id})'.format(self.user))
        print(flush=True)
        self.log.info('Configuration:')
        self.log.info('- Prefix: ' + self.config.prefix)
        self.log.info('- Selfbot: ' + self.format_bool(self.config.selfbot))
        self.log.info('- Private Messages: ' + self.format_bool(self.config.pm))
        self.log.info('- Delete Messages: ' + self.format_bool(self.config.delete))
        print(flush=True)
        self.log.info('RethinkDB:')
        self.log.info('- Server: {0.rhost}:{0.rport} ({0.ruser})'.format(self.config))

        # Connect to database
        connect = await self.db.connect(self.config.rhost, self.config.rport, self.config.ruser, self.config.rpass)
        if connect:
            # Create needed tables
            await self.db.create_table('tags', primary='name')
        else:
            self.log.warning("A database connection could not be established")
            self.log.warning(
                "Commands that require a database connection will be unavailable")
        self.db.ready = True
        print(flush=True)

        # Yaml checks
        self.log.info('Aliases:')
        self.aliases = self.yaml.parse('config/aliases.yml')
        if self.aliases is None:
            self.log.warning("No command aliases will be available. See 'readme.md' for information")
        else:
            self.log.info("- Found aliases")
            for c in self.aliases.copy():
                h = getattr(self.commands, 'c_%s' % c, None)
                if not h:
                    self.log.warning("{} is not a command".format(c))
                    del self.aliases[c]

        print(flush=True)
        self.log.info('Bot is ready!')
        print(flush=True)

    async def on_message(self, message):
        await self.wait_until_ready()
        if not self.db.ready:
            return
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
            # Check aliases
            # This is a relatively expensive loop but should be okay
            # as it is only called after a command prefix is found
            if self.aliases is not None:
                for i in self.aliases:
                    for i2 in self.aliases[i]:
                        if cmd == i2:
                            cmd = i
                            h = getattr(self.commands, 'c_%s' % cmd, None)
                            if not h:  # theoretically this should never be a true statement
                                return
            else:
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
                if self.config.selfbot:
                    return await self.edit_message(message, content, delete=r.delete)
                else:
                    return await self.send_message(message.channel, content, delete=r.delete)
        except InvalidUsage:
            docs = getattr(h, '__doc__', None)
            docs = '\n'.join(l.strip() for l in docs.split('\n'))
            docs = ":warning: Incorrect usage.\n```\n{}\n```".format(
                docs.format(prefix=self.config.prefix))
            if self.config.selfbot:
                return await self.edit_message(message, docs, delete=10)
            return await self.send_message(message.channel, docs, delete=10)
        except Shutdown:
            raise

    async def on_error(self, event, *args, **kwargs):
        et, e, es = sys.exc_info()
        if et == Shutdown:
            self.log.warning("Shutdown signal received. Terminating...")
            await self.logout()
        else:
            traceback.print_exc()

if __name__ == "__main__":
    bot = Turbo()
    bot.run(bot.config.token)
