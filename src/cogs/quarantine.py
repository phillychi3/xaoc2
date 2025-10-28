from typing import Optional
import discord
from discord.ext import commands
from logging import getLogger
from datetime import datetime, timedelta
from core.heat_system import get_heat_system
from core.setting import get_settings

logger = getLogger("xaoc")


class QuarantineSystem(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.logger = getLogger("xaoc")
        self.heat_system = get_heat_system()
        self.settings = get_settings()

        self.quarantine_role_name = "隔離區"

        self.quarantined_users: dict[str, dict[str, list[int]]] = {}

    async def get_or_create_quarantine_role(self, guild: discord.Guild) -> discord.Role | None:
        """獲取或創建隔離區角色"""

        quarantine_role = discord.utils.get(guild.roles, name=self.quarantine_role_name)

        if quarantine_role:
            return quarantine_role

        try:
            quarantine_role = await guild.create_role(
                name=self.quarantine_role_name,
                color=discord.Color.dark_red(),
                hoist=True,
                mentionable=False,
                reason="自動創建隔離區角色",
            )

            self.logger.info(f"已創建隔離區角色: {quarantine_role.name}")

            permissions = discord.Permissions.none()
            permissions.read_messages = True
            permissions.read_message_history = False

            await quarantine_role.edit(permissions=permissions)

            await self.setup_channel_permissions(guild, quarantine_role)

            return quarantine_role

        except discord.Forbidden:
            self.logger.error("無權限創建隔離區角色")
            return None
        except Exception as e:
            self.logger.error(f"創建隔離區角色時發生錯誤: {e}", exc_info=True)
            return None

    async def setup_channel_permissions(self, guild: discord.Guild, quarantine_role: discord.Role):
        """為所有頻道設置隔離區角色的權限"""
        try:
            for channel in guild.text_channels:
                await channel.set_permissions(
                    quarantine_role,
                    send_messages=False,
                    add_reactions=False,
                    reason="隔離區權限設置",
                )

            for channel in guild.voice_channels:
                await channel.set_permissions(quarantine_role, connect=False, reason="隔離區權限設置")

            self.logger.info(f"已為 {len(guild.channels)} 個頻道設置隔離區權限")

        except discord.Forbidden:
            self.logger.error("無權限設置頻道權限")
        except Exception as e:
            self.logger.error(f"設置頻道權限時發生錯誤: {e}", exc_info=True)

    async def quarantine_user(self, guild: discord.Guild, member: discord.Member, reason: str = "自動隔離") -> bool:
        """將用戶移動到隔離區"""
        try:
            quarantine_role = await self.get_or_create_quarantine_role(guild)
            if not quarantine_role:
                return False

            if quarantine_role in member.roles:
                self.logger.info(f"用戶 {member} 已在隔離區")
                return True

            guild_id = str(guild.id)
            user_id = str(member.id)

            if guild_id not in self.quarantined_users:
                self.quarantined_users[guild_id] = {}

            original_roles = [role.id for role in member.roles if role != guild.default_role]
            self.quarantined_users[guild_id][user_id] = original_roles

            roles_to_remove = [role for role in member.roles if role != guild.default_role]
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason=f"隔離: {reason}")

            await member.add_roles(quarantine_role, reason=reason)

            try:
                embed = discord.Embed(
                    title="您已被移至隔離區",
                    description=f"由於可疑活動,您在 **{guild.name}** 已被暫時限制。",
                    color=discord.Color.dark_red(),
                    timestamp=datetime.now(),
                )
                embed.add_field(name="原因", value=reason, inline=False)
                embed.add_field(
                    name="如何解除",
                    value="請聯繫伺服器管理員以了解詳情和解除限制。",
                    inline=False,
                )
                await member.send(embed=embed)
            except discord.Forbidden:
                self.logger.warning(f"無法向用戶 {member} 發送私訊")

            self.logger.warning(f"已將用戶 {member} ({member.id}) 移至隔離區 | 原因: {reason}")

            # log_embed = discord.Embed(
            #     title="用戶已被隔離",
            #     color=discord.Color.dark_red(),
            #     timestamp=datetime.now(),
            # )
            # log_embed.add_field(name="用戶", value=f"{member.mention} ({member.id})", inline=False)
            # log_embed.add_field(name="原因", value=reason, inline=False)

            # heat_value = self.heat_system.get_user_heat_data(str(guild.id), str(member.id)).heat_value
            # danger_level = self.heat_system.get_danger_level(str(guild.id), str(member.id))

            # log_embed.add_field(
            #     name="熱力值",
            #     value=f"{heat_value:.1f} ({danger_level})",
            #     inline=False,
            # )
            return True

        except discord.Forbidden:
            self.logger.error(f"無權限隔離用戶 {member}")
            return False
        except Exception as e:
            self.logger.error(f"隔離用戶時發生錯誤: {e}", exc_info=True)
            return False

    async def release_user(self, guild: discord.Guild, member: discord.Member) -> bool:
        """從隔離區釋放用戶"""
        try:
            quarantine_role = discord.utils.get(guild.roles, name=self.quarantine_role_name)
            if not quarantine_role:
                self.logger.warning("找不到隔離區角色")
                return False

            if quarantine_role not in member.roles:
                self.logger.info(f"用戶 {member} 不在隔離區")
                return False

            await member.remove_roles(quarantine_role, reason="釋放隔離")

            guild_id = str(guild.id)
            user_id = str(member.id)

            if guild_id in self.quarantined_users and user_id in self.quarantined_users[guild_id]:
                original_role_ids = self.quarantined_users[guild_id][user_id]
                roles_to_restore = [guild.get_role(role_id) for role_id in original_role_ids]
                roles_to_restore = [role for role in roles_to_restore if role]

                if roles_to_restore:
                    await member.add_roles(*roles_to_restore, reason="恢復原有角色")

                del self.quarantined_users[guild_id][user_id]

            self.heat_system.reset_user_heat(str(guild.id), str(member.id))

            self.logger.info(f"已將用戶 {member} ({member.id}) 從隔離區釋放")

            try:
                embed = discord.Embed(
                    title="您已從隔離區釋放",
                    description=f"您在 **{guild.name}** 的限制已被解除。",
                    color=discord.Color.green(),
                    timestamp=datetime.now(),
                )
                await member.send(embed=embed)
            except discord.Forbidden:
                self.logger.warning(f"無法向用戶 {member} 發送私訊")

            return True

        except discord.Forbidden:
            self.logger.error(f"無權限釋放用戶 {member}")
            return False
        except Exception as e:
            self.logger.error(f"釋放用戶時發生錯誤: {e}", exc_info=True)
            return False

    @commands.Cog.listener()
    async def on_user_high_risk(self, guild: discord.Guild, member: discord.Member):
        """監聽高風險用戶事件"""
        heat_value = self.heat_system.get_user_heat_data(str(guild.id), str(member.id)).heat_value
        danger_level = self.heat_system.get_danger_level(str(guild.id), str(member.id))

        reason = f"熱力值過高 ({heat_value:.1f}) - {danger_level}"
        await self.quarantine_user(guild, member, reason)

    @commands.command(name="quarantine")
    @commands.has_permissions(moderate_members=True)
    async def quarantine_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "手動隔離"):
        """手動將用戶移至隔離區"""
        if not ctx.guild:
            await ctx.send("此指令只能在伺服器中使用")
            return
        if member == ctx.author:
            await ctx.send("您不能隔離自己")
            return

        if getattr(ctx.author, "top_role", None) is None:
            await ctx.send("無法獲取您的角色資訊")
            return

        if member.top_role >= ctx.author.top_role:  # type: ignore
            await ctx.send("您無法隔離權限等級高於或等於您的用戶")
            return

        success = await self.quarantine_user(ctx.guild, member, reason)
        if success:
            await ctx.send(f"已將 {member.mention} 移至隔離區")
        else:
            await ctx.send("隔離用戶失敗")

    @commands.command(name="release")
    @commands.has_permissions(moderate_members=True)
    async def release_cmd(self, ctx: commands.Context, member: discord.Member):
        """從隔離區釋放用戶"""
        if not ctx.guild:
            await ctx.send("此指令只能在伺服器中使用")
            return
        success = await self.release_user(ctx.guild, member)
        if success:
            await ctx.send(f"已將 {member.mention} 從隔離區釋放")
        else:
            await ctx.send("釋放用戶失敗或用戶不在隔離區")

    @commands.command(name="quarantinelist")
    @commands.has_permissions(manage_messages=True)
    async def quarantine_list(self, ctx: commands.Context):
        """查看隔離區用戶列表"""

        if not ctx.guild:
            await ctx.send("此指令只能在伺服器中使用")
            return
        quarantine_role = discord.utils.get(ctx.guild.roles, name=self.quarantine_role_name)

        if not quarantine_role:
            await ctx.send("隔離區角色不存在")
            return

        quarantined_members = [member for member in ctx.guild.members if quarantine_role in member.roles]

        if not quarantined_members:
            await ctx.send("目前沒有用戶在隔離區")
            return

        embed = discord.Embed(
            title="隔離區用戶列表",
            description=f"共 {len(quarantined_members)} 位用戶",
            color=discord.Color.dark_red(),
            timestamp=datetime.now(),
        )

        for member in quarantined_members[:25]:
            heat_value = self.heat_system.get_user_heat_data(str(ctx.guild.id), str(member.id)).heat_value
            embed.add_field(
                name=f"{member.display_name}",
                value=f"{member.mention}\n熱力值: {heat_value:.1f}",
                inline=True,
            )

        await ctx.send(embed=embed)

    @commands.command(name="setupquarantine")
    @commands.has_permissions(administrator=True)
    async def setup_quarantine(self, ctx: commands.Context):
        """設置隔離區系統 (創建角色和權限)"""
        if not ctx.guild:
            await ctx.send("此指令只能在伺服器中使用")
            return

        await ctx.send("正在設置隔離區系統...")

        quarantine_role = await self.get_or_create_quarantine_role(ctx.guild)

        if quarantine_role:
            await ctx.send(
                f"隔離區系統設置完成！\n角色: {quarantine_role.mention}\n已為 {len(ctx.guild.channels)} 個頻道設置權限"
            )
        else:
            await ctx.send("隔離區系統設置失敗")


async def setup(bot):
    await bot.add_cog(QuarantineSystem(bot))
