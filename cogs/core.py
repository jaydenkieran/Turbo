import datetime
import discord

from discord.ext import commands


class Core:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, name='help', aliases=['stats', 'about'])
    async def help_(self, ctx):
        msg = ctx.message
        embed = discord.Embed(title='Turbo ({})'.format(self.bot._version), color=0x00FF12)
        embed.set_author(name='Jayden Bailey', url='https://github.com/jaydenkieran', icon_url='http://i.imgur.com/tPVwRJ2.jpg')
        cmds = '`, `'.join(self.bot.commands)
        loaded = "`, `".join(self.bot.extensions)
        desc = ":newspaper2: Extensions: `{}`\n:loudspeaker: Commands (`{}`): `{}`\n".format(loaded, self.bot.command_prefix, cmds)
        embed.description = desc

        await self.bot.edit(msg, embed=embed)


def setup(bot):
    bot.add_cog(Core(bot))
