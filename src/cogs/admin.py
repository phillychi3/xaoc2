from datetime import datetime
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from logging import getLogger

from core.heat_system import get_heat_system


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.logger = getLogger("xaoc")
        self.heat_system = get_heat_system()

    @app_commands.command(name="heatstats", description="查看用戶的熱力值統計")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(member="要查看的用戶 (不指定則查看自己)")
    async def heat_stats(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        """查看用戶的熱力值統計"""
        if not interaction.guild:
            await interaction.response.send_message("此指令只能在伺服器中使用", ephemeral=True)
            return
        
        if member is None:
            if isinstance(interaction.user, discord.Member):
                member = interaction.user
            else:
                await interaction.response.send_message("無法取得用戶資訊", ephemeral=True)
                return

        stats = self.heat_system.get_user_stats(str(interaction.guild.id), str(member.id))

        embed = discord.Embed(
            title=f"🌡️ {member.display_name} 的熱力值統計",
            color=discord.Color.orange(),
            timestamp=datetime.now(),
        )

        embed.add_field(name="當前熱力值", value=f"{stats['heat_value']:.1f}", inline=True)
        embed.add_field(name="危險等級", value=stats["danger_level"], inline=True)
        embed.add_field(name="Spam 次數", value=str(stats["spam_count"]), inline=True)
        embed.add_field(name="釣魚嘗試", value=str(stats["phishing_attempts"]), inline=True)
        embed.add_field(name="蜜罐觸發", value=str(stats["honeypot_triggers"]), inline=True)

        if stats["violations"]:
            violations_text = "\n".join(stats["violations"][-5:])
            embed.add_field(name="最近違規記錄", value=f"```{violations_text}```", inline=False)

        embed.set_footer(text=f"最後更新: {stats['last_updated'].strftime('%Y-%m-%d %H:%M:%S')}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="resetheat", description="重置用戶的熱力值 (管理員專用)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(member="要重置熱力值的用戶")
    async def reset_heat(self, interaction: discord.Interaction, member: discord.Member):
        """重置用戶的熱力值 (管理員專用)"""
        if not interaction.guild:
            await interaction.response.send_message("此指令只能在伺服器中使用", ephemeral=True)
            return

        self.heat_system.reset_user_heat(str(interaction.guild.id), str(member.id))
        await interaction.response.send_message(f"✅ 已重置 {member.mention} 的熱力值")

    @app_commands.command(name="highrisk", description="查看高風險用戶列表")
    @app_commands.default_permissions(manage_messages=True)
    async def high_risk_users(self, interaction: discord.Interaction):
        """查看高風險用戶列表"""
        if not interaction.guild:
            await interaction.response.send_message("此指令只能在伺服器中使用", ephemeral=True)
            return
            
        high_risk = self.heat_system.get_high_risk_users(str(interaction.guild.id), threshold=25.0)

        if not high_risk:
            await interaction.response.send_message("✅ 目前沒有高風險用戶", ephemeral=True)
            return

        high_risk.sort(key=lambda x: x[1].heat_value, reverse=True)

        embed = discord.Embed(
            title="⚠️ 高風險用戶列表",
            description=f"共 {len(high_risk)} 位用戶",
            color=discord.Color.red(),
            timestamp=datetime.now(),
        )

        for i, (user_id, heat_data) in enumerate(high_risk[:10], 1):
            member = interaction.guild.get_member(int(user_id))
            member_name = member.mention if member else f"用戶 {user_id}"
            danger_level = self.heat_system.get_danger_level(str(interaction.guild.id), user_id)

            embed.add_field(
                name=f"#{i} {member_name}",
                value=f"熱力值: {heat_data.heat_value:.1f} | {danger_level}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
