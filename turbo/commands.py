import asyncio
import inspect
import traceback
import discord
import random
import re
import subprocess
import logging
import urllib.parse

from bs4 import BeautifulSoup
from functools import wraps
from discord.ext.commands.bot import _get_variable

from .exceptions import InvalidUsage, Shutdown
from .utils import load_json
from .constants import BACKUP_TAGS

log = logging.getLogger(__name__)


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
                return Response(":warning: This command cannot be used. Only read-only commands can be used while the database is unavailable", delete=10)

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
        log.debug("Discriminator timer started")
        self.can_change_name = False
        await asyncio.sleep(60 * 61)  # 1 hour, 1 min (compensating)
        self.can_change_name = True
        log.info(
            "{}changediscrim can now be used again".format(self.config.prefix))

    async def c_ping(self):
        """
        Tests the bot's latency

        {prefix}ping
        """
        return Response(":ping_pong:", delete=5)

    async def c_shutdown(self, channel):
        """
        Shuts down the bot

        {prefix}shutdown
        """
        await self.bot.send_message(channel, ":wave:")
        raise Shutdown()

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
        log.debug("Evaluated: {} - Result was: {}".format(stmt, result))
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
                log.debug('Assuming role provided: ' + id)
                for s in self.bot.servers:
                    role = discord.utils.get(s.roles, id=id)
                    if role:
                        preface = " Role: **{} | {}**\n".format(s, role.name)
            if ':' in id:
                # Assume that an emoji was provided
                log.debug('Assuming emoji provided: ' + id)
                if id.startswith(':'):
                    id = id[1:]
                name = id.rsplit(':', 1)[0]
                preface = " Emote: **{}**\n".format(name)
                id = id.split(':', 1)[1]
            log.debug("Resolved snowflake ID to " + id)
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

    async def c_status(self, author, args, status=None):
        """
        Changes playing status on Discord

        {prefix}status [text]

        If no status is provided, it'll clear the status
        """
        if status is None:
            await self.bot.change_presence(game=None, status=author.status)
            return Response(":speech_left: Cleared status", delete=60)
        else:
            status = ' '.join([status, *args])
            await self.bot.change_presence(game=discord.Game(name=status), status=author.status)
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

        It achieves this by changing your Discord username
        Discord name changes are limited to 2 per hour
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
        log.debug(
            "Changing name from {} to {}".format(self.bot.user.name, name))
        try:
            await self.bot.edit_profile(password=self.config.password, username=name)
        except discord.HTTPException as e:
            log.error(e)
            return Response(":warning: There was a problem. The password in the config may be invalid.", delete=10)
        await asyncio.sleep(3)  # Allow time for websocket event
        log.debug(
            "Discriminator: {} -> {}".format(author.discriminator, self.bot.user.discriminator))
        if self.config.discrimrevert:
            await self.bot.edit_profile(password=self.config.password, username=author.name)
            asyncio.ensure_future(self._discrim_timer())
        return Response(":thumbsup: Changed from `{}` -> `{}`".format(author.discriminator, self.bot.user.discriminator), delete=60)

    async def c_tags(self):
        """
        Get a list of all tags

        {prefix}tags
        """
        if not self.bot.dbfailed:
            cursor = await self.db.get_db().table(self.bot.config.dbtable_tags).run(self.db.db)
            if not cursor.items:
                return Response(":warning: No tags exist (yet)", delete=10)
            tags = [x['name'] for x in cursor.items]
        else:
            tags = load_json(BACKUP_TAGS)
            if not tags:
                return Response(":warning: No tags found in the backup tags file", delete=10)
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
            await self.db.insert(self.bot.config.dbtable_tags, data)
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
            delete = await self.db.delete(self.bot.config.dbtable_tags, name)
            if int(delete['skipped']) != 0:
                return Response(":warning: Could not delete `{}`, does not exist".format(name), delete=10)
            return Response(":thumbsup:", delete=10)
        else:
            raise InvalidUsage()

    async def c_tag(self, message, tag):
        """
        Returns a tag

        {prefix}tag <name>
        """
        content = message.content.replace(
            '{}tag '.format(self.config.prefix), '')
        if not self.bot.dbfailed:
            get = await self.db.get_db().table(self.bot.config.dbtable_tags).get(content).run(self.db.db)
            if get is None:
                return Response(":warning: No tag named `{}`".format(content), delete=10)
            else:
                return Response(get['content'])
        else:
            get = load_json(BACKUP_TAGS)
            if not get:
                return Response(":warning: No tags found in the backup tags file", delete=10)
            else:
                get = get.get(content, default=None)
                if get is None:
                    return Response(":warning: No tag with that name in the backup tags file", delete=10)
                else:
                    return Response(get)

    @requires_db
    async def c_cleartags(self):
        """
        Clears all tags

        {prefix}cleartags
        """
        await self.db.delete(self.bot.config.dbtable_tags)
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
            output = subprocess.Popen(' '.join(args), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except Exception as e:
            output = e
        while output is not None:
            retcode = output.poll()
            if retcode is not None:
                # done
                output = output.communicate()[0].decode()
                break
            else:
                # still running
                await asyncio.sleep(1)
        return Response("```xl\n--- Subprocess ---\n{}\n```".format(output))

    async def c_cat(self):
        """
        Sends a random cat picture

        {prefix}cat
        """
        cat = await self.req.get('http://random.cat/meow')
        return Response(cat['file'])

    async def c_youtube(self, args):
        """
        Searches YouTube from given query
        Returns the 5 results

        {prefix}youtube <query>
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

            prefix = ":clapper: "
            if '/user/' in l['href'] or '/channel/' in l['href']:
                prefix = ":bust_in_silhouette: "
            if '&list=' in l['href']:
                prefix = ':book: '

            response += "\n{0}`{1}` - <https://youtube.com{2}>".format(prefix, l['title'], l['href'])
            amount -= 1
        return Response(response)

    async def c_presence(self, author, option=None):
        """
        Changes presence status on Discord

        {prefix}presence <online/idle/dnd/invisible>

        Invisible makes you appear offline.
        Leave blank to reset presence to online.
        """
        afk = False

        if option is None:
            option = 'online'
        else:
            option = option.lower()

        if any(s == option for s in [e.value for e in discord.Status]):
            if option == 'idle':
                afk = True
            await self.bot.change_presence(game=author.game, status=option, afk=afk)
            return Response(":white_check_mark: Set presence to {}!".format(option))
        else:
            raise InvalidUsage()

    async def c_ghissue(self, repo, args):
        """
        Returns the top GitHub issue results in a repo for a query

        {prefix}ghissue <repo> <query>
        """
        if not args:
            raise InvalidUsage()
        args = ' '.join(args)

        if '/' not in repo:
            return Response(":warning: The repository name should be formatted like: `hammerandchisel/discord-api-docs`", delete=10)

        url = "https://api.github.com/repos/{0}/issues".format(repo)
        req = await self.req.get(url, json=True)

        matching = []
        for i in req:
            if args.lower() in i['title'].lower():
                matching.append(i)
            elif args.lower() in i['body'].lower():
                matching.append(i)
            # TODO: Fuzzy searching

        if not matching:
            return Response(":no_entry_sign: No results found in `{}` for `{}`".format(repo, args), delete=10)

        result = ":mag: Found these results in `{}` for `{}`\n".format(repo, args)
        for i in matching:
            result += "\n#{} ({}) `{}`: <{}>".format(i['number'], i['state'], i['title'], i['html_url'])
        return Response(result)
