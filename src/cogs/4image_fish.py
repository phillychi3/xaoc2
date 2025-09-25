import discord
from discord.ext import commands
import re
from logging import getLogger


class Image4Fish(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.logger = getLogger("xaoc")

    def detect_4image_attack(self, content):
        cdn_pattern = r"https://cdn\.discordapp\.com/attachments/\d+/\d+/([1-4]\.jpg)\?"
        matches = re.findall(cdn_pattern, content)
        expected_files = {"1.jpg", "2.jpg", "3.jpg", "4.jpg"}
        found_files = set(matches)

        if found_files == expected_files:
            self.logger.info(f"檢測到4圖span: {found_files}")
            return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        if self.detect_4image_attack(message.content):
            self.logger.warning(
                f"檢測到4圖攻擊! 來自用戶: {message.author} ({message.author.id}) "
                f"頻道: {message.channel} ({message.channel.id})"
            )

            try:
                await message.delete()
                self.logger.info(f"成功刪除4圖span消息，用戶: {message.author}")
            except Exception as e:
                self.logger.error(f"無法處理4圖span消息: {e}, 用戶: {message.author}")


def setup(bot):
    bot.add_cog(Image4Fish(bot))
