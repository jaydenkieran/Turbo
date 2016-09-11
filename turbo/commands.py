import os
import asyncio
import inspect
import traceback
import discord
import datetime
import random
import re
import rethinkdb as r

from functools import wraps
from discord.ext.commands.bot import _get_variable

from .exceptions import InvalidUsage


class Response:

    """
    Response class for commands
    """

    def __init__(self, content, reply=True, delete=0):
        self.content = content
        self.reply = reply
        self.delete = delete


class Commands:

    """
    Stores all the commands for the bot
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.log = bot.log
        self.db = bot.db

        self.can_change_name = True

    def requires_selfbot(func):
        """
        Requires the bot to be running with the selfbot bool in the config set to True
        """
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            message = _get_variable('message')

            if not message or self.config.selfbot:
                return await func(self, *args, **kwargs)
            else:
                return Response(":warning: This command can only be used with selfbots", delete=10)

        return wrapper

    async def _discrim_timer(self):
        self.log.debug("Discriminator timer started")
        self.can_change_name = False
        await asyncio.sleep(60 * 61)  # 1 hour, 1 min (compensating)
        self.can_change_name = True
        self.log.info("{}changediscrim can now be used again".format(self.config.prefix))

    async def c_ping(self):
        """
        Tests the bot's latency

        {prefix}ping
        """
        return Response(":ping_pong:", delete=10)

    async def c_shutdown(self, channel, option):
        """
        Shuts down the bot with a specific option

        {prefix}shutdown <normal/n/hard/h>

        'normal/n' will logout of Discord properly (safer)
        'hard/h' will forcefully terminate the script (quicker)
        """
        if any(s in option for s in ['normal', 'n']):
            await self.bot.send_message(channel, ":wave:")
            # Cleanup
            await self.bot.logout()
            pending = asyncio.Task.all_tasks()
            gathered = asyncio.gather(*pending)
            try:
                gathered.cancel()
                self.bot.loop.run_until_complete(gathered)
                gathered.exception()
            except:
                pass
        elif any(s in option for s in ['hard', 'h']):
            await self.bot.send_message(channel, ":wave:")
            os._exit(1)
        else:
            raise InvalidUsage()

    async def c_help(self, cmd=None):
        """
        Provides helpful information

        {prefix}help [command]

        If a command is omitted, it will return a list of commands
        If a command is given, it will give the docs for that command
        """
        if cmd:
            h = getattr(self, 'c_%s' % cmd, None)
            if not h:
                return Response(":warning: `{}` is not a valid command".format(cmd), delete=10)
            docs = getattr(h, '__doc__', None)
            docs = '\n'.join(l.strip() for l in docs.split('\n'))
            return Response("```\n{}\n```".format(
                docs.format(prefix=self.config.prefix)), reply=True, delete=60)
        else:
            commands = []
            for a in dir(self):
                if a.startswith('c_'):
                    cname = a.replace('c_', '').lower()
                    commands.append("{}{}".format(self.config.prefix, cname))
            return Response("Commands:\n`{}`".format("`, `".join(commands)), delete=60)

    async def c_eval(self, message, server, channel, author, stmt, args):
        """
        Evaluates Python code

        {prefix}eval <code>

        If the result is a coroutine, it will be awaited
        """
        stmt = ' '.join([stmt, *args])
        try:
            result = eval(stmt)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            exc = traceback.format_exc().splitlines()
            result = exc[-1]
        self.log.debug("Evaluated: {} - Result was: {}".format(stmt, result))
        return Response("```py\n# Input\n{}\n# Output\n{}\n```".format(stmt, result))

    async def c_snowflake(self, author, id=None):
        """
        Get the creation time in UTC of a Discord ID

        {prefix}snowflake [id/@user/#channel/emote/@role]

        If no ID is provided, it'll use the invoker's ID
        However, if the bot is acting as a selfbot, it'll use it's own
        """
        if id is None:
            if self.config.selfbot:
                id = self.bot.user.id
            else:
                id = author.id
        preface = " "
        if '<' in id:
            # Assume that a numerical ID wasn't actually given
            for i in ['<', '>', '#', '@']:
                # Replace common delimiters
                id = id.replace(i, '')
            if id.startswith('&'):
                # Assume that a role was provided
                id = id.replace('&', '')
                self.log.debug('Assuming role provided: ' + id)
                for s in self.bot.servers:
                    role = discord.utils.get(s.roles, id=id)
                    if role:
                        preface = " Role: **{} | {}**\n".format(s, role.name)
            if ':' in id:
                # Assume that an emoji was provided
                self.log.debug('Assuming emoji provided: ' + id)
                if id.startswith(':'):
                    id = id[1:]
                name = id.rsplit(':', 1)[0]
                preface = " Emote: **{}**\n".format(name)
                id = id.split(':', 1)[1]
            self.log.debug("Resolved snowflake ID to " + id)
        try:
            sfid = int(id)
        except ValueError:
            return Response(":warning: `{}` is not a valid ID".format(id), delete=10)

        # Try and resolve it to an object for no reason really
        member = discord.utils.get(self.bot.get_all_members(), id=id)
        if member:
            preface = " User: **{}**\n".format(member)
        channel = discord.utils.get(self.bot.get_all_channels(), id=id)
        if channel:
            preface = " Channel: **{0.server} | #{0.name}**\n".format(channel)
        emoji = discord.utils.get(self.bot.get_all_emojis(), id=id)
        if emoji:
            preface = " Emote: **{}**\n".format(emoji.name)
        server = discord.utils.get(self.bot.servers, id=id)
        if server:
            preface = " Server: **{}**\n".format(server)
        message = discord.utils.get(self.bot.messages, id=id)
        if message:
            preface = " Message: Sent in **{0.server} | #{0.name}**\n".format(message.channel)

        snowflake = discord.utils.snowflake_time(sfid)
        time = snowflake.strftime("**%a %d %b %y** (**%X** UTC)")
        return Response(":snowflake:{}`{}` was created: {}".format(preface, id, time))

    async def c_status(self, args, status=None):
        """
        Changes playing status on Discord

        {prefix}status [text]

        If no status is provided, it'll clear the status
        """
        if status is None:
            await self.bot.change_status(game=None)
            return Response(":speech_left: Cleared status", delete=60)
        else:
            status = ' '.join([status, *args])
            await self.bot.change_status(game=discord.Game(name=status))
            return Response(":speech_left: Changed status to **{}**".format(status), delete=60)

    async def c_discrim(self, author, discrim=None):
        """
        Displays users with matching discriminator that are visible

        {prefix}discrim [discriminator]

        If you don't provide a discrim, it'll use the invoker's discrim
        However, if the bot is acting as a selfbot, it'll use it's own
        """
        if discrim is None:
            if self.config.selfbot:
                discrim = self.bot.user.discriminator
            else:
                discrim = author.discriminator
        else:
            try:
                discrim = int(discrim)
            except ValueError:
                return Response(":warning: `{}` is not a valid discriminator".format(discrim), delete=10)
        has_discrim = set([x.name for x in self.bot.get_all_members() if x.discriminator == discrim])
        if not has_discrim:
            return Response(":warning: No names with the discriminator `{}`".format(discrim), delete=10)
        return Response(":crayon: Names using `{}`\n`{}`".format(discrim, '`, `'.join(has_discrim)))

    @requires_selfbot
    async def c_changediscrim(self, author):
        """
        Changes the user's discriminator

        {prefix}changediscrim

        Discord name changes are limited to 2 per hour
        This command changes your name twice to achieve a discrim change
        As a result, do not try to use this command more than once per hour

        The command should not run if it detects it hasn't been an hour yet
        Do not rely on this functionality, though
        """
        if not self.config.password:
            return Response(":warning: This command only works when Password is set in the config", delete=10)
        if not self.can_change_name:
            return Response(":warning: This command cannot be used yet. It has not been 1 hour since last usage", delete=10)
        has_discrim = list(set([x.name for x in self.bot.get_all_members() if x.discriminator == author.discriminator and x.name != author.name]))
        if not has_discrim:
            return Response(":warning: No names with the discriminator `{}`".format(author.discriminator), delete=10)
        name = random.choice(has_discrim)
        self.log.debug("Changing name from {} to {}".format(self.bot.user.name, name))
        try:
            await self.bot.edit_profile(password=self.config.password, username=name)
        except discord.HTTPException as e:
            self.log.error(e)
            return Response(":warning: There was a problem. The password in the config may be invalid.", delete=10)
        await asyncio.sleep(3)  # Allow time for websocket event
        self.log.debug("Discriminator: {} -> {}".format(author.discriminator, self.bot.user.discriminator))
        await self.bot.edit_profile(password=self.config.password, username=author.name)
        asyncio.ensure_future(self._discrim_timer())
        return Response(":thumbsup: Changed from `{}` -> `{}`".format(author.discriminator, self.bot.user.discriminator), delete=60)

    async def c_tags(self):
        """
        Get a list of all tags

        {prefix}tags
        """
        cursor = await self.db.get_db().table('tags').run(self.db.db)
        if not cursor.items:
            return Response(":warning: No tags exist (yet)", delete=10)
        tags = [x['name'] for x in cursor.items]
        return Response(":pen_ballpoint: **Tags**\n`{}`".format('`, `'.join(tags)), delete=60)

    async def c_createtag(self, message):
        """
        Create a tag

        {prefix}createtag "name" "tag"
        """
        content = re.findall('"([^"]*)"', message.content)
        if len(content) == 2:
            name, content = content
            data = {"name": name, "content": content}
            insert = await self.db.insert('tags', data)
            return Response(":thumbsup:", delete=10)
        else:
            raise InvalidUsage()

    async def c_deletetag(self, message):
        """
        Delete a tag

        {prefix}deletetag "name"
        """
        content = re.findall('"([^"]*)"', message.content)
        if len(content) == 1:
            name = content[0]
            delete = await self.db.delete('tags', name)
            if int(delete['skipped']) != 0:
                return Response(":warning: Could not delete `{}`, does not exist".format(name), delete=10)
            return Response(":thumbsup:", delete=10)
        else:
            raise InvalidUsage()
