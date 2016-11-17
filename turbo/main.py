import discord
import inspect
import asyncio
import time
import sys
import traceback
import logging

from .utils import Config, Yaml, load_json, dump_json
from .commands import Commands, Response
from .exceptions import InvalidUsage, Shutdown
from .constants import VERSION, USER_AGENT, BACKUP_TAGS
from .database import Database
from .req import HTTPClient

log = logging.getLogger(__name__)


class Turbo(discord.Client):

    def __init__(self):
        self.config = Config('config/turbo.ini')

        super().__init__()
        self.http.user_agent = USER_AGENT
        self.db = Database(self)

        self.req = HTTPClient(loop=self.loop)
        self.commands = Commands(self)

        log.info("Turbo ({}). Connecting...".format(VERSION))

    def run(self, token):
        """
        Override's discord.py's function for running the bot
        """
        try:
            super().run(token, bot=(not self.config.selfbot))
        except discord.LoginFailure:
            log.critical("Incorrect login token")
            if not self.config.selfbot:
                log.critical(
                    "Using your own token? Change 'selfbot' to 'True' in the config")
            else:
                log.critical(
                    "Using an OAuth account? Change 'selfbot' to 'False' in the config")
        except discord.HTTPException as e:
            log.critical(e)

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

    async def send_message(self, dest, content=None, embed=None, *, tts=False, delete=0):
        """
        Overrides discord.py's function for sending a message
        """
        if content is None and embed is None:
            log.warning('send_message was called but no content was given')
            return
        if isinstance(content, discord.Embed):
            embed = content
            content = None

        msg = None
        try:
            if embed:
                msg = await super().send_message(dest, embed=embed)
            else:
                msg = await super().send_message(dest, content, tts=tts)
            log.debug(
                'Sent message ID {} in #{}'.format(msg.id, dest.name))

            if msg and delete and self.config.delete:
                asyncio.ensure_future(self._delete_after(msg, delete))
        except discord.Forbidden:
            log.warning(
                "No permission to send a message to #{}".format(dest.name))
        except discord.NotFound:
            log.warning(
                "Could not find channel #{} to send a message to".format(dest.name))
        except discord.HTTPException as e:
            log.warning(
                "Problem sending a message in #{}: {}".format(dest.name, e))
        return msg

    async def edit_message(self, message, content, *, delete=0):
        """
        Overrides discord.py's function for editing a message
        """
        msg = None
        try:
            msg = await super().edit_message(message, content)
            log.debug(
                'Edited message ID {} in #{}'.format(msg.id, msg.channel))

            if msg and delete and self.config.delete:
                asyncio.ensure_future(self._delete_after(msg, delete))
        except discord.Forbidden:
            log.warning(
                "No permission to edit a message in #{}".format(message.channel))
        except discord.NotFound:
            log.warning(
                "Could not find message ID {} to edit".format(message.id))
        except discord.HTTPException as e:
            log.warning(
                "Problem editing a message in #{}: {}".format(message.channel, e))
        return msg

    async def delete_message(self, msg):
        """
        Overrides discord.py's function for deleting a message
        """
        try:
            await super().delete_message(msg)
            log.debug(
                'Deleted message ID {} in #{}'.format(msg.id, msg.channel.name))
        except discord.Forbidden:
            log.warning(
                "No permission to delete a message in #{}".format(msg.channel.name))
        except discord.HTTPException as e:
            log.warning(
                "Problem deleting a message in #{}: {}".format(msg.channel.name, e))

    async def _delete_after(self, msg, time):
        """
        Deletes a message after a given amount of time
        """
        log.debug(
            "Scheduled message ID {} to delete ({}s)".format(msg.id, time))
        await asyncio.sleep(time)
        await self.delete_message(msg)

    async def on_ready(self):
        """
        Called when the bot is connected to Discord
        """
        self.started = time.time()
        log.debug("Bot start time is {}".format(self.started))
        log.info('Logged in as {0} ({0.id})'.format(self.user))
        print(flush=True)
        log.info('General:')
        log.info('- Prefix: ' + self.config.prefix)
        log.info('- Selfbot: ' + self.format_bool(self.config.selfbot))
        log.info('- Private Messages: ' + self.format_bool(self.config.pm))
        log.info('- Delete Messages: ' + self.format_bool(self.config.delete))
        print(flush=True)
        log.info('Advanced:')
        log.info('- No Database: ' + self.format_bool(self.config.nodatabase))
        log.info('- Read Aliases: ' + self.format_bool(self.config.readaliases))
        log.info('- Selfbot Message Editing: ' + self.format_bool(self.config.selfbotmessageedit))
        log.info('- Discrim Name Revert: ' + self.format_bool(self.config.discrimrevert))
        print(flush=True)
        log.info('Database:')
        log.info('- Server: {0.rhost}:{0.rport} ({0.ruser})'.format(self.config))

        # Connect to database
        self.dbfailed = False
        if not self.config.nodatabase:
            connect = await self.db.connect(self.config.rhost, self.config.rport, self.config.ruser, self.config.rpass)
            if connect:
                # Create needed tables
                await self.db.create_table(self.config.dbtable_tags, primary='name')
                if self.config.backuptags:
                    # Dump any existing tags to backup file
                    log.info("Backing up existing tags to JSON file...")
                    cursor = await self.db.get_db().table(self.config.dbtable_tags).run(self.db.db)
                    current_backup = load_json(BACKUP_TAGS)
                    for i in cursor.items:
                        name = i['name']
                        current_backup[name] = i['content']
                    dump_json(BACKUP_TAGS, current_backup)
                    log.info("Tags have been backed up to {} in case of a database outage".format(BACKUP_TAGS))
            else:
                log.warning("A database connection could not be established")
                self.dbfailed = True
        else:
            log.warning("Skipped database connection per configuration file")
            self.dbfailed = True
        if self.dbfailed:
            log.warning(
                "As the database is unavailable, tags cannot be created or deleted, but tags that exist in the backup JSON file can be triggered.")
        self.db.ready = True
        print(flush=True)

        # Yaml checks
        log.info('Aliases:')
        if self.config.readaliases:
            self.aliases = Yaml.parse('config/aliases.yml')
            if self.aliases is None:
                log.warning("No command aliases will be available. See 'readme.md' for information")
            else:
                for c in self.aliases.copy():
                    h = getattr(self.commands, 'c_%s' % c, None)
                    if not h:
                        log.warning("{} is not a command".format(c))
                        del self.aliases[c]
                headings = [c for c in self.aliases]
                aliases = []
                for i in headings:
                    aliases += [a for a in self.aliases[i]]
                log.info("- Found {} aliases".format(len(aliases)))
                dupes = set([x for x in aliases if aliases.count(x) > 1])
                if dupes:
                    # there are duplicate aliases
                    for i in dupes:
                        log.warning("{} is an alias used by multiple commands. Check the aliases file".format(i))
        else:
            self.aliases = None
            log.warning("Skipped aliases checking per configuration file")

        print(flush=True)
        log.info('Bot is ready!')
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
                            log.debug("Detected alias {} -> {}".format(cmd, i))
                            cmd = i
                            h = getattr(self.commands, 'c_%s' % cmd, None)
                            if not h:  # theoretically this should never be a true statement
                                return
            else:
                return

        if not message.channel.is_private:
            log.info(
                "[Command] {0} [{1.server} | #{1}] - {2}".format(message.author, message.channel, content))
        else:
            log.info(
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
                if self.config.selfbot and self.config.selfbotmessageedit:
                    return await self.edit_message(message, content, delete=r.delete)
                else:
                    return await self.send_message(message.channel, content, delete=r.delete)
        except InvalidUsage:
            log.debug("Invalid usage for command {} used by {}".format(cmd, message.author))
            docs = getattr(h, '__doc__', None)
            docs = '\n'.join(l.strip() for l in docs.split('\n'))
            docs = ":warning: Incorrect usage.\n```\n{}\n```".format(
                docs.format(prefix=self.config.prefix))
            if self.config.selfbot and self.config.selfbotmessageedit:
                return await self.edit_message(message, docs, delete=10)
            return await self.send_message(message.channel, docs, delete=10)
        except Shutdown:
            raise
        except Exception as e:
            e = ":warning: An exception occurred: `{}`. For more information, see the console.".format(e)
            if self.config.selfbot and self.config.selfbotmessageedit:
                return await self.edit_message(message, e, delete=10)
            return await self.send_message(message.channel, e, delete=10)
            raise

    async def on_error(self, event, *args, **kwargs):
        et, e, es = sys.exc_info()
        if et == Shutdown:
            log.debug("Shutdown signal received. Terminating...")
            await self.logout()
        else:
            traceback.print_exc()

if __name__ == "__main__":
    raise Shutdown()
