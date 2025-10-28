import discord
from discord.ext import commands
from logging import getLogger
from core.setting import get_settings
from core.heat_system import get_heat_system


class Honeypot(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.logger = getLogger("xaoc")
        self.heat_system = get_heat_system()

        self.honeypot_channel_id = get_settings().honeypot.channel_id

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        if str(message.channel.id) == self.honeypot_channel_id:
            if not message.guild:  # stupid pylance
                return
            self.heat_system.add_honeypot_violation(str(message.guild.id), str(message.author.id))

            heat_value = self.heat_system.get_user_heat_data(str(message.guild.id), str(message.author.id)).heat_value
            danger_level = self.heat_system.get_danger_level(str(message.guild.id), str(message.author.id))

            self.logger.warning(
                f"檢測到蜜罐觸發! 來自用戶: {message.author} ({message.author.id}) "
                f"頻道: {message.channel} ({message.channel.id}) | "
                f"熱力值: {heat_value:.1f} | 危險等級: {danger_level}"
            )

            try:
                await message.delete()

                if message.guild:
                    self.bot.dispatch("user_high_risk", message.guild, message.author)
                    self.logger.warning(f"用戶 {message.author} 觸發蜜罐")

            except Exception as e:
                self.logger.error(f"無法處理蜜罐頻道消息: {e}, 用戶: {message.author}")


async def setup(bot):
    await bot.add_cog(Honeypot(bot))
