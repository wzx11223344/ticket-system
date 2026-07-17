"""工具函数."""

import os
import sys
from typing import Optional


def resolve_storage_path(custom_path: Optional[str] = None) -> str:
    """解析数据库文件路径。

    优先使用 TMS_DATA_DIR 环境变量，否则使用默认路径。
    """
    base = custom_path or os.environ.get("TMS_DATA_DIR", "")
    if base:
        path = os.path.join(base, "tickets.json")
    else:
        # 项目根目录下的 data 文件夹
        project_root = _find_project_root()
        path = os.path.join(project_root, "data", "tickets.json")
    return os.path.abspath(path)


def resolve_backup_dir(custom_path: Optional[str] = None) -> str:
    """解析备份文件夹路径."""
    base = custom_path or os.environ.get("TMS_DATA_DIR", "")
    if base:
        path = os.path.join(base, "backups")
    else:
        project_root = _find_project_root()
        path = os.path.join(project_root, "data", "backups")
    return os.path.abspath(path)


def ensure_data_dir(data_path: str) -> None:
    """确保数据目录存在."""
    os.makedirs(os.path.dirname(data_path), exist_ok=True)


def _find_project_root() -> str:
    """从当前文件向上回溯，找到 ticket-system 项目根目录."""
    # 从 tms/utils.py 向上回溯
    current = os.path.dirname(os.path.abspath(__file__))  # .../ticket-system/tms
    parent = os.path.dirname(current)  # .../ticket-system
    # 验证：如果存在 app.py 或 pyproject.toml 就认为正确
    if os.path.exists(os.path.join(parent, "app.py")) or os.path.exists(os.path.join(parent, "pyproject.toml")):
        return parent
    # 回退到当前工作目录
    return os.getcwd()


def colorize(text: str, color: str) -> str:
    """终端颜色包裹（Windows/macOS/Linux 通用）."""
    colors = {
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "magenta": "35",
        "cyan": "36",
        "bold": "1",
    }
    code = colors.get(color, "0")
    # Windows 10+ 支持 ANSI，如不支持则返回纯文本
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            return text
    return f"\033[{code}m{text}\033[0m"


def print_header(text: str) -> None:
    """打印分隔标题."""
    width = 60
    print()
    print("=" * width)
    print(f"  {text}")
    print("=" * width)
