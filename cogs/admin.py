from discord.ext import commands
import traceback
import discord
import inspect
from contextlib import redirect_stdout
import io
import asyncio


class REPL:
    """
    REPL script taken from R. Danny modified to better suit Turbo.
    """

    def __init__(self, bot):
        self.bot = bot
        self.sessions = set()

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    def get_syntax_error(self, e):
        return '```py\n{0.text}{1:>{0.offset}}\n{2}: {0}```'.format(e, '^', type(e).__name__)

    @commands.command(pass_context=True)
    async def repl(self, ctx):
        msg = ctx.message

        variables = {
            'ctx': ctx,
            'bot': self.bot,
            'message': msg,
            'server': msg.server,
            'channel': msg.channel,
            'author': msg.author,
            '_': None,
        }

        if msg.channel.id in self.sessions:
            await self.bot.edit(msg, 'Already evaluating.')
            return

        self.sessions.add(msg.channel.id)
        await self.bot.edit(msg, 'Evaluating.')
        while True:
            response = await self.bot.wait_for_message(author=msg.author, channel=msg.channel,
                                                       check=lambda m: m.content.startswith('`'))

            cleaned = self.cleanup_code(response.content)

            if cleaned in ('quit', 'exit', 'exit()'):
                await self.bot.edit(response, 'Exiting.')
                self.sessions.remove(msg.channel.id)
                return

            executor = exec
            if cleaned.count('\n') == 0:
                # single statement, potentially 'eval'
                try:
                    code = compile(cleaned, '<repl session>', 'eval')
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is exec:
                try:
                    code = compile(cleaned, '<repl session>', 'exec')
                except SyntaxError as e:
                    await self.bot.edit(response, self.get_syntax_error(e))
                    continue

            variables['message'] = response

            fmt = None
            stdout = io.StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as e:
                value = stdout.getvalue()
                fmt = '```py\n{}{}\n```'.format(value, traceback.format_exc())
            else:
                value = stdout.getvalue()
                if result is not None:
                    fmt = '```py\n{}{}\n```'.format(value, result)
                    variables['_'] = result
                elif value:
                    fmt = '```py\n{}\n```'.format(value)

            try:
                if fmt is not None:
                    if len(fmt) > 2000:
                        await self.bot.edit(response, 'Content too big to be printed.')
                    else:
                        await self.bot.edit(response, fmt)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await self.bot.edit(response, 'Unexpected error: `{}`'.format(e))

################################################################################


class Admin:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def shutdown(self, ctx):
        await self.bot.edit(ctx.message, "Terminating")
        await asyncio.sleep(1)
        await self.bot.logout()

    @commands.command(pass_context=True, name='reload')
    async def reload_(self, ctx, *, module: str):
        try:
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
        except Exception as e:
            await self.bot.edit(ctx.message, 'There was a problem: `{}`'.format(e))
        else:
            await self.bot.edit(ctx.message, 'Reloaded module: `{}`'.format(module))


################################################################################


def setup(bot):
    bot.add_cog(REPL(bot))
    bot.add_cog(Admin(bot))
