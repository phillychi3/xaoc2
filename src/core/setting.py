from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional, Dict, Any
import json
import os


class HoneypotSettings(BaseModel):
    channel_id: Optional[str] = Field(default=None, description="蜜罐頻道ID")

    @field_validator("channel_id")
    @classmethod
    def validate_channel_id(cls, v):
        if v is not None and not v.isdigit():
            raise ValueError("channel_id 必須是純數字字符串")
        return v


class LogSettings(BaseModel):
    level: str = Field(default="INFO", description="日誌級別")
    file_path: str = Field(default="logs/xaoc.log", description="日誌文件路径")
    format: str = Field(
        default="[xaoc] %(asctime)s %(levelname)s: %(message)s", description="日誌格式"
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"日誌級別必須是 {valid_levels} 中的一個")
        return v.upper()


class MemberFilterSettings(BaseModel):
    enabled: bool = Field(default=True, description="是否啟用成員過濾")
    min_account_age_days: int = Field(default=1, description="帳號最小年齡(天)")
    kick_new_accounts: bool = Field(default=True, description="是否踢出新帳號")

    @field_validator("min_account_age_days")
    @classmethod
    def validate_min_age(cls, v):
        if v < 0:
            raise ValueError("帳號最小年齡不能為負數")
        return v


class Settings(BaseSettings):
    honeypot: HoneypotSettings = Field(default_factory=HoneypotSettings)
    logging: LogSettings = Field(default_factory=LogSettings)
    member_filter: MemberFilterSettings = Field(default_factory=MemberFilterSettings)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_nested_delimiter": "__",
        "case_sensitive": False,
    }

    @classmethod
    def from_json_file(cls, file_path: str = "setting.json") -> "Settings":
        if not os.path.exists(file_path):
            default_settings = cls()
            default_settings.save_to_json(file_path)
            return default_settings

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(**data)

    def save_to_json(self, file_path: str = "setting.json") -> None:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, ensure_ascii=False, indent=4)

    def update_from_dict(self, data: Dict[str, Any]) -> "Settings":
        return self.model_copy(update=data)


_settings: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    """
    獲取全局設置實例

    Args:
        reload: 是否重新加載設置

    Returns:
        Settings實例
    """
    global _settings

    if _settings is None or reload:
        _settings = Settings.from_json_file()

    return _settings
