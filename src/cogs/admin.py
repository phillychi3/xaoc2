from datetime import datetime
from typing import Optional
import discord
from discord.ext import commands
from logging import getLogger

from core.heat_system import get_heat_system


class Image4Fish(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.logger = getLogger("xaoc")
        self.heat_system = get_heat_system()

    @commands.command(name="heatstats")
    @commands.has_permissions(manage_messages=True)
    async def heat_stats(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """查看用戶的熱力值統計"""
        if not ctx.guild:
            return
        if member is None:
            if isinstance(ctx.author, discord.Member):
                member = ctx.author
            else:
                return

        stats = self.heat_system.get_user_stats(str(ctx.guild.id), str(member.id))

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

        await ctx.send(embed=embed)

    @commands.command(name="resetheat")
    @commands.has_permissions(administrator=True)
    async def reset_heat(self, ctx: commands.Context, member: discord.Member):
        """重置用戶的熱力值 (管理員專用)"""
        if not ctx.guild:
            return

        self.heat_system.reset_user_heat(str(ctx.guild.id), str(member.id))
        await ctx.send(f"已重置 {member.mention} 的熱力值")

    @commands.command(name="highrisk")
    @commands.has_permissions(manage_messages=True)
    async def high_risk_users(self, ctx: commands.Context):
        """查看高風險用戶列表"""
        if not ctx.guild:
            return
        high_risk = self.heat_system.get_high_risk_users(str(ctx.guild.id), threshold=25.0)

        if not high_risk:
            await ctx.send("目前沒有高風險用戶")
            return

        high_risk.sort(key=lambda x: x[1].heat_value, reverse=True)

        embed = discord.Embed(
            title="高風險用戶列表",
            description=f"共 {len(high_risk)} 位用戶",
            color=discord.Color.red(),
            timestamp=datetime.now(),
        )

        for i, (user_id, heat_data) in enumerate(high_risk[:10], 1):
            member = ctx.guild.get_member(int(user_id))
            member_name = member.mention if member else f"用戶 {user_id}"
            danger_level = self.heat_system.get_danger_level(str(ctx.guild.id), user_id)

            embed.add_field(
                name=f"#{i} {member_name}",
                value=f"熱力值: {heat_data.heat_value:.1f} | {danger_level}",
                inline=False,
            )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Image4Fish(bot))
