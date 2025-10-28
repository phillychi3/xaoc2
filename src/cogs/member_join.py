import discord
from discord.ext import commands
from logging import getLogger
from core.heat_system import get_heat_system
import datetime


class MemberFilter(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.logger = getLogger("xaoc")
        self.heat_system = get_heat_system()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        account_age = datetime.datetime.now(datetime.timezone.utc) - member.created_at
        days_old = account_age.days

        if days_old < 1:
            try:
                await member.kick(reason=f"帳號年齡過新 ({days_old} 天)")
                self.logger.warning(f"已踢出新成員 {member} ({member.id}) - 帳號年齡: {days_old} 天 (小於1天)")

            except discord.Forbidden:
                self.logger.error(f"無權限踢出新成員 {member}")
            except Exception as e:
                self.logger.error(f"踢出新成員時發生錯誤 {member}: {e}")

        elif days_old < 7:
            self.heat_system.add_new_account_violation(str(member.guild.id), str(member.id))

            heat_value = self.heat_system.get_user_heat_data(str(member.guild.id), str(member.id)).heat_value

            self.logger.warning(
                f"高風險新成員加入 {member} ({member.id}) | 帳號年齡: {days_old} 天 | 熱力值: {heat_value:.1f}"
            )

        else:
            self.logger.info(f"新成員加入 {member} ({member.id}) - 帳號年齡: {days_old} 天")


async def setup(bot):
    await bot.add_cog(MemberFilter(bot))
