#!/usr/bin/env python3
"""Ticket Management System — CLI + Web 双模式入口.

用法:
  python app.py create --title "修复bug" --desc "..." --priority high --assignee 张三
  python app.py list
  python app.py list --status open --priority high
  python app.py view --id TKT-001
  python app.py update --id TKT-001 --status in_progress
  python app.py assign --id TKT-001 --to 李四
  python app.py comment --id TKT-001 --msg "已修复"
  python app.py stats
  python app.py board
  python app.py web
  python app.py backup --suffix before_migration
"""

import sys

from tms.cli_handler import (
    handle_create,
    handle_list,
    handle_view,
    handle_update,
    handle_assign,
    handle_comment,
    handle_stats,
    handle_board,
    handle_backup,
)
from tms.api import run_web_server


COMMANDS = {
    "create": handle_create,
    "list": handle_list,
    "view": handle_view,
    "update": handle_update,
    "assign": handle_assign,
    "comment": handle_comment,
    "stats": handle_stats,
    "board": handle_board,
    "backup": handle_backup,
}


def main():
    if len(sys.argv) < 2:
        print("用法: python app.py <command> [options]")
        print()
        print("可用命令:")
        for cmd in COMMANDS:
            print(f"  {cmd}")
        print("  web        启动 Web 看板服务器")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "web":
        host = "127.0.0.1"
        port = 5000
        # 解析 --host 和 --port 参数
        for i, arg in enumerate(args):
            if arg == "--host" and i + 1 < len(args):
                host = args[i + 1]
            elif arg == "--port" and i + 1 < len(args):
                port = int(args[i + 1])
        run_web_server(host=host, port=port)
    elif command in COMMANDS:
        COMMANDS[command](args)
    else:
        print(f"未知命令: {command}")
        print("可用命令: " + ", ".join(COMMANDS.keys()) + ", web")
        sys.exit(1)


if __name__ == "__main__":
    main()
