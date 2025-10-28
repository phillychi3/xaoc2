from datetime import datetime, timedelta
from typing import Optional
import logging
from .server_cache import ServerCache, UserHeatData

logger = logging.getLogger("xaoc")


class HeatSystem:
    """熱力系統管理器"""

    HEAT_SPAM_MESSAGE = 10.0  # 垃圾訊息
    HEAT_SPAM_BURST = 25.0  # 短時間大量訊息
    HEAT_PHISHING_LINK = 50.0  # 釣魚連結
    HEAT_HONEYPOT_TRIGGER = 100
    HEAT_NEW_ACCOUNT = 15.0  # 新帳號可疑行為
    HEAT_USER_INSTALL_SPAM = 40.0  # User install spam
    HEAT_DECAY_RATE = 2.0  # 每小時自然衰減率

    def __init__(self, server_cache: ServerCache):
        self.server_cache = server_cache

    def get_user_heat_data(self, guild_id: str, user_id: str) -> UserHeatData:
        """獲取用戶熱力值資料"""
        return self.server_cache.get_user_heat_data(guild_id, user_id)

    def add_heat(self, guild_id: str, user_id: str, amount: float, reason: str) -> None:
        """增加熱力值"""
        heat_data = self.get_user_heat_data(guild_id, user_id)
        heat_data.heat_value += amount
        heat_data.last_updated = datetime.now()
        heat_data.violations.append(f"[{datetime.now()}] {reason} (+{amount})")
        logger.info(f"用戶 {user_id} 熱力值增加 {amount} (原因: {reason}), 當前: {heat_data.heat_value}")

    def reduce_heat(self, guild_id: str, user_id: str, amount: float) -> None:
        """減少熱力值 (自然衰減)"""
        heat_data = self.get_user_heat_data(guild_id, user_id)
        heat_data.heat_value = max(0, heat_data.heat_value - amount)
        heat_data.last_updated = datetime.now()

    def get_danger_level(self, guild_id: str, user_id: str) -> str:
        """獲取危險等級"""
        heat_data = self.get_user_heat_data(guild_id, user_id)
        heat_value = heat_data.heat_value

        if heat_value >= 100:
            return "極度危險"
        elif heat_value >= 75:
            return "高度危險"
        elif heat_value >= 50:
            return "中度危險"
        elif heat_value >= 25:
            return "低度危險"
        else:
            return "安全"

    def should_quarantine(self, guild_id: str, user_id: str) -> bool:
        """是否應該被隔離"""
        heat_data = self.get_user_heat_data(guild_id, user_id)
        return heat_data.heat_value >= 75

    def should_timeout(self, guild_id: str, user_id: str) -> bool:
        """是否應該被禁言"""
        heat_data = self.get_user_heat_data(guild_id, user_id)
        return heat_data.heat_value >= 50

    def add_spam_violation(self, guild_id: str, user_id: str, is_burst: bool = False):
        """添加垃圾訊息違規"""
        heat_data = self.get_user_heat_data(guild_id, user_id)
        heat_data.spam_count += 1

        if is_burst:
            self.add_heat(guild_id, user_id, self.HEAT_SPAM_BURST, "短時間大量訊息")
        else:
            self.add_heat(guild_id, user_id, self.HEAT_SPAM_MESSAGE, "垃圾訊息")

    def add_phishing_violation(self, guild_id: str, user_id: str):
        """添加釣魚連結違規"""
        heat_data = self.get_user_heat_data(guild_id, user_id)
        heat_data.phishing_attempt_count += 1
        self.add_heat(guild_id, user_id, self.HEAT_PHISHING_LINK, "釣魚連結")

    def add_honeypot_violation(self, guild_id: str, user_id: str):
        """添加蜜罐觸發違規"""
        heat_data = self.get_user_heat_data(guild_id, user_id)
        heat_data.honeypot_trigger_count += 1
        self.add_heat(guild_id, user_id, self.HEAT_HONEYPOT_TRIGGER, "觸發蜜罐")

    def add_new_account_violation(self, guild_id: str, user_id: str):
        """添加新帳號可疑行為"""
        self.add_heat(guild_id, user_id, self.HEAT_NEW_ACCOUNT, "新帳號可疑行為")

    def add_user_install_spam(self, guild_id: str, user_id: str):
        """添加 user install spam 違規"""
        self.add_heat(guild_id, user_id, self.HEAT_USER_INSTALL_SPAM, "User install spam")

    def decay_heat(self):
        """自然衰減所有用戶的熱力值"""
        now = datetime.now()
        for server in self.server_cache.servers:
            for user in server.users:
                if user.heat_data.heat_value > 0:
                    user.heat_data.heat_value = max(0, user.heat_data.heat_value - self.HEAT_DECAY_RATE)
                    user.heat_data.last_updated = now
        logger.info(f"熱力值自然衰減完成，衰減量: {self.HEAT_DECAY_RATE}")

    def get_high_risk_users(self, guild_id: str, threshold: float = 50.0) -> list[tuple[str, UserHeatData]]:
        """獲取高風險用戶列表"""
        server = self.server_cache.get_server(guild_id)
        if not server:
            return []

        high_risk = []
        for user in server.users:
            if user.heat_data.heat_value >= threshold:
                high_risk.append((user.id, user.heat_data))

        return high_risk

    def reset_user_heat(self, guild_id: str, user_id: str):
        """重置用戶熱力值"""
        heat_data = self.get_user_heat_data(guild_id, user_id)
        heat_data.heat_value = 0.0
        heat_data.violations.clear()
        heat_data.spam_count = 0
        heat_data.phishing_attempt_count = 0
        heat_data.honeypot_trigger_count = 0
        heat_data.last_updated = datetime.now()
        logger.info(f"已重置用戶 {user_id} 的熱力值")

    def get_user_stats(self, guild_id: str, user_id: str) -> dict:
        """獲取用戶統計資訊"""
        heat_data = self.get_user_heat_data(guild_id, user_id)
        return {
            "heat_value": heat_data.heat_value,
            "danger_level": self.get_danger_level(guild_id, user_id),
            "spam_count": heat_data.spam_count,
            "phishing_attempts": heat_data.phishing_attempt_count,
            "honeypot_triggers": heat_data.honeypot_trigger_count,
            "violations": heat_data.violations[-10:],  # 最近10次違規
            "last_updated": heat_data.last_updated,
        }


_server_cache: Optional[ServerCache] = None
_heat_system: Optional[HeatSystem] = None


def get_server_cache() -> ServerCache:
    """獲取全局 ServerCache"""
    global _server_cache
    if _server_cache is None:
        _server_cache = ServerCache()
    return _server_cache


def get_heat_system() -> HeatSystem:
    """獲取全局熱力系統"""
    global _heat_system
    if _heat_system is None:
        _heat_system = HeatSystem(get_server_cache())
    return _heat_system
