import discord
from discord.ext import commands
from logging import getLogger
from core.setting import get_settings
import datetime


class Honeypot(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.logger = getLogger("xaoc")

        self.honeypot_channel_id = get_settings().honeypot.channel_id

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        if str(message.channel.id) == self.honeypot_channel_id:
            self.logger.warning(
                f"檢測到蜜罐觸發! 來自用戶: {message.author} ({message.author.id}) "
                f"頻道: {message.channel} {message.channel.id})"
            )
            try:
                await message.delete()
                await message.author.timeout(until=datetime.timedelta(minutes=10))  # type: ignore
                self.logger.info(f"成功刪除蜜罐頻道消息，用戶: {message.author}")
            except Exception as e:
                self.logger.error(f"無法處理蜜罐頻道消息: {e}, 用戶: {message.author}")


def setup(bot):
    bot.add_cog(Honeypot(bot))
