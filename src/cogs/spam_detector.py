from typing import Optional
import discord
from discord.ext import commands, tasks
from logging import getLogger
from collections import defaultdict, deque
from datetime import datetime, timedelta
from core.heat_system import get_heat_system
from core.server_cache import ServerCache

logger = getLogger("xaoc")


class SpamDetector(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.logger = getLogger("xaoc")
        self.heat_system = get_heat_system()
        self.server_cache = ServerCache()

        self.message_history: defaultdict[int, deque] = defaultdict(lambda: deque(maxlen=10))

        self.MAX_MESSAGES_PER_INTERVAL = 5  # 時間區間內最大訊息數
        self.TIME_INTERVAL = 5  # 秒數
        self.MAX_IDENTICAL_MESSAGES = 3  # 最大重複訊息數
        self.MENTION_SPAM_THRESHOLD = 5  # 最大 mention 數量

        self.cleanup_history.start()

    def cog_unload(self):
        self.cleanup_history.cancel()

    @tasks.loop(minutes=5)
    async def cleanup_history(self):
        """定期清理舊的訊息歷史"""
        cutoff_time = datetime.now() - timedelta(minutes=10)
        for user_id in list(self.message_history.keys()):
            history = self.message_history[user_id]

            while history and history[0][0] < cutoff_time:
                history.popleft()

            if not history:
                del self.message_history[user_id]

    @cleanup_history.before_loop
    async def before_cleanup_history(self):
        await self.bot.wait_until_ready()

    def check_message_spam(self, user_id: int, message: discord.Message) -> tuple[bool, str]:
        """
        檢查訊息是否為 spam
        返回: (是否為spam, 原因)
        """
        now = datetime.now()
        history = self.message_history[user_id]
        history.append((now, message.content.lower()))

        recent_messages = [msg for msg in history if now - msg[0] <= timedelta(seconds=self.TIME_INTERVAL)]
        if len(recent_messages) > self.MAX_MESSAGES_PER_INTERVAL:
            return True, f"短時間內發送過多訊息 ({len(recent_messages)}條/{self.TIME_INTERVAL}秒)"

        if len(recent_messages) >= self.MAX_IDENTICAL_MESSAGES:
            contents = [msg[1] for msg in recent_messages]
            if len(set(contents)) == 1 and contents[0]:
                return True, f"重複發送相同訊息 ({self.MAX_IDENTICAL_MESSAGES}次)"

        if len(message.mentions) > self.MENTION_SPAM_THRESHOLD:
            return True, f"過多 mention ({len(message.mentions)}個)"

        if message.content.count("\n") > 30:
            return True, "訊息包含過多換行"

        return False, ""

    async def handle_spam(self, message: discord.Message, reason: str, is_burst: bool = False):
        """處理檢測到的 spam"""
        try:
            if not message.guild:
                return

            await message.delete()

            self.heat_system.add_spam_violation(str(message.guild.id), str(message.author.id), is_burst=is_burst)

            heat_value = self.heat_system.get_user_heat_data(str(message.guild.id), str(message.author.id)).heat_value
            danger_level = self.heat_system.get_danger_level(str(message.guild.id), str(message.author.id))

            self.logger.warning(
                f"檢測到 Spam | 用戶: {message.author} ({message.author.id}) | "
                f"原因: {reason} | 熱力值: {heat_value:.1f} | "
                f"危險等級: {danger_level}"
            )

            if self.heat_system.should_quarantine(str(message.guild.id), str(message.author.id)):
                self.bot.dispatch("user_high_risk", message.guild, message.author)
                self.logger.warning(f"用戶 {message.author} 達到隔離門檻")

            elif self.heat_system.should_timeout(str(message.guild.id), str(message.author.id)):
                timeout_duration = timedelta(minutes=10)
                await message.author.timeout(timeout_duration, reason=f"Spam 檢測: {reason}")
                self.logger.info(f"已禁言用戶 {message.author} 10分鐘")

            heat_value = self.heat_system.get_user_heat_data(str(message.guild.id), str(message.author.id)).heat_value
            if heat_value < 50:
                try:
                    danger_level = self.heat_system.get_danger_level(str(message.guild.id), str(message.author.id))
                    await message.channel.send(
                        f"{message.author.mention} 請勿發送垃圾訊息",
                        delete_after=5,
                    )
                except Exception:
                    pass

        except discord.Forbidden:
            self.logger.error(f"無權限處理 spam 訊息，用戶: {message.author}")
        except Exception as e:
            self.logger.error(f"處理 spam 時發生錯誤: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if message.author.guild_permissions.administrator or message.author.guild_permissions.manage_messages:  # type: ignore
            return

        is_spam, reason = self.check_message_spam(message.author.id, message)

        if is_spam:
            is_burst = "短時間內發送過多訊息" in reason
            await self.handle_spam(message, reason, is_burst=is_burst)


async def setup(bot):
    await bot.add_cog(SpamDetector(bot))
