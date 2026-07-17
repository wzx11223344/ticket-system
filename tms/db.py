"""JSON 文件持久化层 — 轻量级，零外部依赖."""

import json
import os
import threading
import shutil
from datetime import datetime, timezone
from typing import Optional


class BaseStorage:
    """存储抽象基类."""

    def load(self) -> dict[str, dict]:
        raise NotImplementedError

    def save(self, data: dict[str, dict]) -> None:
        raise NotImplementedError


class JsonStorage(BaseStorage):
    """基于 JSON 文件的持久化实现，读写锁保护."""

    def __init__(self, filepath: str, backup_dir: Optional[str] = None):
        self.filepath = os.path.abspath(filepath)
        self.backup_dir = os.path.abspath(backup_dir) if backup_dir else ""
        self._lock = threading.Lock()

    # ---- 公开方法 ----

    def load(self) -> dict[str, dict]:
        """载入 JSON 数据."""
        with self._lock:
            if not os.path.exists(self.filepath):
                return {}
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, OSError):
                return {}

    def save(self, data: dict[str, dict]) -> None:
        """写入 JSON 数据."""
        with self._lock:
            os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
            # 先写入临时文件防止写中断损坏
            tmp = self.filepath + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            os.replace(tmp, self.filepath)

    def backup(self, suffix: Optional[str] = None) -> str:
        """备份当前数据文件，返回备份路径."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"数据文件不存在: {self.filepath}")

        suffix = suffix or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        os.makedirs(self.backup_dir, exist_ok=True)
        backup_path = os.path.join(self.backup_dir, f"tickets_backup_{suffix}.json")
        shutil.copy2(self.filepath, backup_path)
        return backup_path

    def restore(self, backup_path: str) -> None:
        """从备份文件恢复数据."""
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        with open(backup_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.save(data)

    def list_backups(self) -> list[str]:
        """列出所有备份文件."""
        if not os.path.isdir(self.backup_dir):
            return []
        files = [os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir)
                 if f.startswith("tickets_backup_") and f.endswith(".json")]
        return sorted(files, reverse=True)
