import discord
from discord.ext import commands
import os
import asyncio
import logging
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()


debug_guild = discord.Object(id=623509187371991060)
debug = False

logger = logging.getLogger("xaoc")

logger.setLevel(logging.INFO)
formatter = logging.Formatter("[xaoc] %(asctime)s %(levelname)s: %(message)s")
log_path = Path("logs/xaoc.log")
log_path.parent.mkdir(parents=True, exist_ok=True)
file_handler = logging.FileHandler(log_path, encoding="utf-8")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


class botconfig(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all(),
            activity=discord.Game("α - TEST"),
            *args,
            **kwargs,
        )

    async def setup_hook(self):
        self.remove_command("help")
        path = os.path.dirname(os.path.abspath(__file__))
        for filename in os.listdir(os.path.join(path, "cogs")):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    logger.info(f"加載 {filename[:-3]} 完成")
                except Exception as e:
                    logger.error(f"加載 {filename[:-3]} 失敗：{e}")

    async def on_ready(self):
        logger.info(f"登入成功 {self.user}")
        logger.info(f"機器人ID {self.user.id}") # type: ignore
        logger.info(f"總共有 {len(self.guilds)} 個伺服器")
        logger.info(f"總共有 {len(self.commands)} 個指令")
        logger.info(f"是否為測試模式: {debug}")


bot = botconfig()


async def main():
    logger.info("機器人啟動中")
    token = os.getenv("TOKEN")
    if token is None:
        logger.error("找不到TOKEN")
        return
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
