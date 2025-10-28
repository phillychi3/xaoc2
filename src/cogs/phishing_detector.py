import discord
from discord.ext import commands
from logging import getLogger


logger = getLogger("xaoc")


class PhishingDetector(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.logger = getLogger("xaoc")

    async def handle_phishing(self, message: discord.Message, url: str, reasons: list[str]): ...


async def setup(bot):
    await bot.add_cog(PhishingDetector(bot))
