import json
import os


def load_settings(file_path="setting.json"):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"設置文件 {file_path} 不存在")

    with open(file_path, "r", encoding="utf-8") as f:
        settings = json.load(f)

    return settings
