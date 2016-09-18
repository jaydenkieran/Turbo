import os
import asyncio
import inspect
import traceback
import discord
import random
import re
import subprocess
import urllib.parse

from bs4 import BeautifulSoup
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
        self.req = bot.req

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

    def requires_db(func):
        """
        Requires a database connection
        """
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            message = _get_variable('message')

            if not message or self.db.db is not None:
                return await func(self, *args, **kwargs)
            else:
                return Response(":warning: This command cannot be used - the database is unavailable", delete=10)

        return wrapper

    def creator_only(func):
        """
        Requires the bot's application creator to be the one using the command
        """
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            message = _get_variable('message')

            if self.bot.user.bot:
                owner = (await self.bot.application_info()).owner.id
            else:
                owner = self.bot.user.id

            if not message or message.author.id == owner:
                return await func(self, *args, **kwargs)
            else:
                return Response(":warning: This command cannot be used - only the bot application creator can use this command to prevent harm", delete=10)

        return wrapper

    async def _discrim_timer(self):
        """
        Utility function working in conjunction with changediscrim command
        Do not use this with any other method
        """
        self.log.debug("Discriminator timer started")
        self.can_change_name = False
        await asyncio.sleep(60 * 61)  # 1 hour, 1 min (compensating)
        self.can_change_name = True
        self.log.info(
            "{}changediscrim can now be used again".format(self.config.prefix))

    async def c_ping(self):
        """
        Tests the bot's latency

        {prefix}ping
        """
        return Response(":ping_pong:", delete=5)

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

    @creator_only
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
        return Response("```xl\n--- In ---\n{}\n--- Out ---\n{}\n```".format(stmt, result))

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
            preface = " Message: Sent in **{0.server} | #{0.name}**\n".format(
                message.channel)

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
        has_discrim = set(
            [x.name for x in self.bot.get_all_members() if x.discriminator == discrim])
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
        has_discrim = list(set([x.name for x in self.bot.get_all_members(
        ) if x.discriminator == author.discriminator and x.name != author.name]))
        if not has_discrim:
            return Response(":warning: No names with the discriminator `{}`".format(author.discriminator), delete=10)
        name = random.choice(has_discrim)
        self.log.debug(
            "Changing name from {} to {}".format(self.bot.user.name, name))
        try:
            await self.bot.edit_profile(password=self.config.password, username=name)
        except discord.HTTPException as e:
            self.log.error(e)
            return Response(":warning: There was a problem. The password in the config may be invalid.", delete=10)
        await asyncio.sleep(3)  # Allow time for websocket event
        self.log.debug(
            "Discriminator: {} -> {}".format(author.discriminator, self.bot.user.discriminator))
        await self.bot.edit_profile(password=self.config.password, username=author.name)
        asyncio.ensure_future(self._discrim_timer())
        return Response(":thumbsup: Changed from `{}` -> `{}`".format(author.discriminator, self.bot.user.discriminator), delete=60)

    @requires_db
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

    @requires_db
    async def c_createtag(self, message):
        """
        Create a tag

        {prefix}createtag <"name"> <"tag">
        """
        content = re.findall('"([^"]*)"', message.content)
        if len(content) == 2:
            name, content = content
            data = {"name": name, "content": content}
            await self.db.insert('tags', data)
            return Response(":thumbsup:", delete=10)
        else:
            raise InvalidUsage()

    @requires_db
    async def c_deletetag(self, message):
        """
        Delete a tag

        {prefix}deletetag <"name">
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

    @requires_db
    async def c_tag(self, message, tag):
        """
        Returns a tag

        {prefix}tag <name>
        """
        content = message.content.replace(
            '{}tag '.format(self.config.prefix), '')
        get = await self.db.get_db().table('tags').get(content).run(self.db.db)
        if get is None:
            return Response(":warning: No tag named `{}`".format(content), delete=10)
        else:
            return Response(get['content'])

    @requires_db
    async def c_cleartags(self):
        """
        Clears all tags

        {prefix}cleartags
        """
        await self.db.delete('tags')
        return Response(":thumbsup:", delete=10)

    async def c_stats(self):
        """
        Prints statistics
        """
        response = "```xl"

        # Bot
        m, s = divmod(int(self.bot.get_uptime()), 60)
        h, m = divmod(m, 60)
        response += "\nUptime: %d:%02d:%02d" % (h, m, s)

        # User
        response += "\n\nUsers: {} ({} unique)".format(
            len(list(self.bot.get_all_members())), len(set(self.bot.get_all_members())))
        response += "\nAvatars: {} ({} unique)".format(
            len([x for x in self.bot.get_all_members() if x.avatar]), len(set([x for x in self.bot.get_all_members() if x.avatar])))
        response += "\nBots: {} ({} unique)".format(
            len([x for x in self.bot.get_all_members() if x.bot]), len(set([x for x in self.bot.get_all_members() if x.bot])))

        # Server
        response += "\n\nServers: {}".format(len(self.bot.servers))
        response += "\nRequires 2FA: {}".format(
            len([x for x in self.bot.servers if x.mfa_level == 1]))
        response += "\nHas Emojis: {}".format(
            len([x for x in self.bot.servers if x.emojis]))

        # Other
        response += "\n\nPMs: {}".format(len(self.bot.private_channels))
        response += "\n```"
        return Response(response)

    @creator_only
    async def c_subprocess(self, args):
        """
        Uses subprocess to run a console command
        This should not be used if you do not know what you're doing
        This makes it easier to update the bot and perform actions
        Without having to SSH into the bot itself

        {prefix}subprocess
        """
        if not args:
            raise InvalidUsage()
        try:
            output = subprocess.check_output(args, universal_newlines=True)
        except Exception as e:
            output = e
        return Response("```xl\n--- Subprocess ---\n{}\n```".format(output))

    async def c_cat(self):
        """
        Sends a random cat picture

        {prefix}cat
        """
        cat = await self.req.get('http://random.cat/meow')
        return Response(cat['file'])

    async def c_yt(self, args):
        """
        Searches YouTube from given query
        Returns the first page of results

        {prefix}yt <query>
        """
        if not args:
            raise InvalidUsage()

        args = ' '.join(args)
        search = urllib.parse.quote(args)
        html = await self.req.get('https://www.youtube.com/results?search_query=' + search, json=False)
        soup = BeautifulSoup(html, "html.parser")
        response = "YouTube results for **{}**".format(args)
        amount = 5
        for l in soup.findAll(attrs={'class': 'yt-uix-tile-link'}):
            if amount <= 0:
                break

            if 'watch?' in l['href']:
                prefix = ":clapper: "
            if '/user/' in l['href']:
                prefix = ":bust_in_silhouette: "
            if '&list=' in l['href']:
                prefix = ':book: '

            response += "\n{0}`{1}` - <https://youtube.com{2}>".format(prefix, l['title'], l['href'])
            amount -= 1
        return Response(response)
