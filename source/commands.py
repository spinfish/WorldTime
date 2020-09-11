from datetime import datetime
import typing

import discord
from discord.ext import commands
import pytz

from source.utils import converters
from source.utils.custom_help import CustomHelpCommand
from source.utils.common import tz_format

class WtCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = CustomHelpCommand()
        bot.help_command.cog = self

        self.userdb = bot.userdb  # just to be sure :^)

    def cog_unload(self):
        self.bot.help_command = CustomHelpCommand()

    def format_user(self, member: discord.Member) -> str:
        """Given a member, returns a formatted string showing their username and nickname
        prepared for result output."""

        full_name = discord.utils.escape_markdown(str(member))

        if member.nick is None:
            return f'**{full_name}**'

        nickname = discord.utils.escape_markdown(member.nick)
        return f'**{nickname}** ({full_name})'

    def format_users(self, users: typing.List[discord.Member]) -> str:
        """Given a list of members, pretty-formats each one and returns the list joined by `, `.
        If the list of users is longer than 10, it is sliced to that length and the list is
        appended with `and more...`"""

        if len(users) > 10:
            users = users[:-10]
            modified = [*map(self.format_user, users)]
            modified.append('and more...')
        else:
            modified = [*map(self.format_user, users)]

        return ', '.join(modified)

    @commands.group(invoke_without_command=True, cooldown_after_parsing=True, aliases=['tz'])
    async def timezone(self, ctx):
        """A base command for interacting with the bot's main feature, timezones."""
        await ctx.send_help(ctx.command)

    @timezone.command(name='set')
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def tz_set(self, ctx, timezone: converters.TZConverter):
        """Registers or updates **your** timezone with the bot."""

        await self.userdb.update_user(ctx.guild.id, ctx.author.id, timezone)
        await channel.send(f'\U00002705 Your timezone has been set to {timezone}.')

    @timezone.command(name='setfor')
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.has_permissions(manage_guild=True)
    async def tz_setfor(self, ctx, target: discord.Member, timezone: converters.TZConverter):
        """Registers or updates the timezone of someone else in the server.
        This can only be used by members with the `Manage Server` permission."""

        await self.userdb.update_user(ctx.guild.id, target.id, timezone)
        await channel.send(f'\U00002705 Set timezone for **{str(target)}** to {timezone}.')

    @timezone.command(name='remove', aliases=['wipe'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def tz_remove(self, ctx):
        """Removes your data associated with this server from the bot. This cannot be undone."""

        await self.userdb.delete_user(ctx.guild.id, ctx.author.id)
        await channel.send('\U00002705 Your timezone has been removed.')

    @timezone.command(name='removefor')
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.has_permissions(manage_guild=True)
    async def tz_removefor(self, ctx, *, target: discord.Member):
        """Removes someone else's timezone data from this server from the bot. This cannot be undone.
        This can only be used by members with the `Manage Server` permission."""

        await self.userdb.delete_user(ctx.guild.id, target.id)
        await channel.send(f'\U00002705 Removed zone information for **{str(target)}**.')

    @timezone.command(name='show')
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def tz_show(self, ctx, *, user: discord.Member = None):
        """Either shows your or someone else's timezone."""
        await self._show(ctx, user)

    @timezone.command(name='list')
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def tz_list(self, ctx):
        """Shows a list of timezones registered in the guild."""
        await self._list_guild(ctx)

    async def _list_guild(self, ctx):
        """The helper function behind the command `tz list`."""

        userdict = await self.userdb.get_users(ctx.guild.id)

        if userdict is None:
            return await ctx.send(
                '\U0000274c No users with registered time zones have been active in the last 30 days.')

        iterating_dict = sorted(userdict.items())  # this sorts the entries by timezone
        tzs = []

        for k, v in iterating_dict:
            members = []

            for id_ in v:
                try:
                    member = await commands.MemberConverter().convert(ctx, str(id_))
                except commands.BadArgument:
                    continue
                else:
                    members.append(member)

            tzs.append(f"{k[4:]}: {self.format_users(members)}")

        embed = discord.Embed(description='\n'.join(tzs))
        await ctx.send(embed=embed)

    async def _show(self, ctx, user):
        """The helper function behind the command `tz show`."""

        if user is None:
            user = ctx.author

        result = await self.userdb.get_user(ctx.guild.id, user.id)

        if result is None:
            if user == ctx.author:
                return await ctx.send(
                    f'\U0000274c You do not have a time zone. Set it with `{ctx.prefix}set`.')
                    # i use ctx.prefix here in case you want to add support for custom prefixes in the future

            return await ctx.send('\U0000274c The given user does not have a time zone set.')

        embed = discord.Embed(
            description=f'{tz_format(result)[4:]}: {self.format_user(user)}')

        await channel.send(embed=embed)

def setup(bot):
    bot.add_cog(WtCommands(bot))
