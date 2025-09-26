import discord
from discord.ext import commands
from logging import getLogger
import datetime


class MemberFilter(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.logger = getLogger("xaoc")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            ...
        if member.created_at > datetime.datetime.now() - datetime.timedelta(days=1):
            try:
                await member.kick(reason="Account too young")
                self.logger.info(f"已踢出新成員 {member} (帳號過新)")
            except Exception as e:
                self.logger.error(f"無法踢出新成員 {member}: {e}")


def setup(bot):
    bot.add_cog(MemberFilter(bot))
