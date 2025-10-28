from typing import Optional, cast
import discord
from discord.ext import commands
from logging import getLogger
from collections import defaultdict, deque
from datetime import datetime, timedelta
from core.heat_system import get_heat_system

logger = getLogger("xaoc")


class UserInstallSpamDetector(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.logger = getLogger("xaoc")
        self.heat_system = get_heat_system()

        self.command_history: defaultdict[int, deque] = defaultdict(lambda: deque(maxlen=20))

        self.MAX_COMMANDS_PER_MINUTE = 10
        self.MAX_IDENTICAL_COMMANDS = 5
        self.COMMAND_SPAM_WINDOW = 60

    def check_command_spam(self, user_id: int, command_name: str) -> tuple[bool, str]:
        now = datetime.now()
        history = self.command_history[user_id]

        history.append((now, command_name))

        window_start = now - timedelta(seconds=self.COMMAND_SPAM_WINDOW)
        recent_commands = [cmd for cmd in history if cmd[0] >= window_start]

        if len(recent_commands) > self.MAX_COMMANDS_PER_MINUTE:
            return True, f"短時間內執行過多指令 ({len(recent_commands)}次/{self.COMMAND_SPAM_WINDOW}秒)"

        command_counts = defaultdict(int)
        for _, cmd_name in recent_commands:
            command_counts[cmd_name] += 1

        for cmd_name, count in command_counts.items():
            if count >= self.MAX_IDENTICAL_COMMANDS:
                return True, f"重複執行相同指令 ({cmd_name} x{count})"

        return False, ""

    async def handle_command_spam(
        self,
        interaction: discord.Interaction,
        command_name: str,
        reason: str,
    ):
        try:
            if not interaction.guild:
                return
            self.heat_system.add_user_install_spam(str(interaction.guild.id), str(interaction.user.id))

            heat_value = self.heat_system.get_user_heat_data(
                str(interaction.guild.id), str(interaction.user.id)
            ).heat_value
            danger_level = self.heat_system.get_danger_level(str(interaction.guild.id), str(interaction.user.id))

            self.logger.warning(
                f"檢測到 User Install Spam | 用戶: {interaction.user} ({interaction.user.id}) | "
                f"指令: {command_name} | 原因: {reason} | "
                f"熱力值: {heat_value:.1f} | 危險等級: {danger_level}"
            )

            if self.heat_system.should_quarantine(str(interaction.guild.id), str(interaction.user.id)):
                member = interaction.guild.get_member(interaction.user.id)
                if member:
                    self.bot.dispatch("user_high_risk", interaction.guild, member)
                    self.logger.warning(f"用戶 {interaction.user} 因 user install spam 達到隔離門檻")

            elif self.heat_system.should_timeout(str(interaction.guild.id), str(interaction.user.id)):
                member = interaction.guild.get_member(interaction.user.id)
                if member:
                    timeout_duration = timedelta(minutes=15)
                    await member.timeout(timeout_duration, reason=f"User Install Spam: {reason}")
                    self.logger.info(f"已禁言用戶 {interaction.user} 15分鐘")

        except Exception as e:
            self.logger.error(f"處理 user install spam 時發生錯誤: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.application_command:
            return

        if interaction.user.bot:
            return

        command_name = interaction.data.get("name", "unknown") if interaction.data else "unknown"

        is_spam, reason = self.check_command_spam(interaction.user.id, command_name)

        if is_spam:
            await self.handle_command_spam(interaction, command_name, reason)

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: discord.app_commands.Command):
        pass

    @commands.command(name="commandstats")
    @commands.has_permissions(manage_messages=True)
    async def command_stats(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        if member is None:
            if isinstance(ctx.author, discord.Member):
                member = ctx.author
            else:
                return

        history = self.command_history.get(member.id, deque())

        if not history:
            await ctx.send(f"{member.mention} 尚未使用任何指令")
            return

        now = datetime.now()
        window_start = now - timedelta(minutes=5)
        recent_commands = [cmd for cmd in history if cmd[0] >= window_start]

        command_counts = defaultdict(int)
        for _, cmd_name in recent_commands:
            command_counts[cmd_name] += 1

        display_name = getattr(member, "display_name", getattr(member, "name", str(member.id)))
        embed = discord.Embed(
            title=f"{display_name} 的指令統計",
            description="最近 5 分鐘的指令使用情況",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )

        embed.add_field(name="總指令數", value=str(len(recent_commands)), inline=True)
        embed.add_field(name="不同指令數", value=str(len(command_counts)), inline=True)

        if command_counts:
            top_commands = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            commands_text = "\n".join(f"• `{cmd}`: {count} 次" for cmd, count in top_commands)
            embed.add_field(name="最常用指令", value=commands_text, inline=False)

        if ctx.guild:
            heat_value = self.heat_system.get_user_heat_data(str(ctx.guild.id), str(member.id)).heat_value
            danger_level = self.heat_system.get_danger_level(str(ctx.guild.id), str(member.id))
            embed.add_field(
                name="當前熱力值",
                value=f"{heat_value:.1f} ({danger_level})",
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.command(name="clearcommandhistory")
    @commands.has_permissions(administrator=True)
    async def clear_command_history(self, ctx: commands.Context, member: discord.Member):
        """清除用戶的指令歷史記錄"""
        if member.id in self.command_history:
            del self.command_history[member.id]
            await ctx.send(f"已清除 {member.mention} 的指令歷史記錄")
        else:
            await ctx.send(f"{member.mention} 沒有指令歷史記錄")


async def setup(bot):
    await bot.add_cog(UserInstallSpamDetector(bot))
