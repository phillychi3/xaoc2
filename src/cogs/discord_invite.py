import discord
from discord.ext import commands
import re
from logging import getLogger


class InviteLink(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.logger = getLogger("xaoc")

    def detect_server_invitelink(self, content):
        cdn_pattern = r"(https?:\/\/)?(www.)?(discord.(gg|io|me|li)|discordapp.com\/invite|discord.com\/invite)\/[^\s\/]+?(?=\b)"
        return re.match(cdn_pattern, content) is not None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        if self.detect_server_invitelink(message.content):
            self.logger.warning(
                f"檢測到邀請鏈接! 來自用戶: {message.author} ({message.author.id}) "
                f"頻道: {message.channel} ({message.channel.id})"
            )
            try:
                await message.delete()
                self.logger.info(f"成功刪除邀請鏈接消息，用戶: {message.author}")
            except Exception as e:
                self.logger.error(f"無法處理邀請鏈接消息: {e}, 用戶: {message.author}")


def setup(bot):
    bot.add_cog(InviteLink(bot))
