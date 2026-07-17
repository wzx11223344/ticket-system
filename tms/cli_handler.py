"""CLI 命令处理 — 格式化输出与交互逻辑."""

import sys
from typing import Optional

from tms.core import (
    create_ticket,
    update_ticket,
    assign_ticket,
    add_comment,
    get_ticket,
    list_tickets,
    get_ticket_stats,
    generate_kanban_board,
    VALID_STATUSES,
    VALID_PRIORITIES,
    Ticket,
)
from tms.db import JsonStorage
from tms.utils import colorize, print_header, resolve_storage_path, resolve_backup_dir, ensure_data_dir


def _get_storage(custom_path: Optional[str] = None) -> JsonStorage:
    """获取存储实例."""
    data_path = resolve_storage_path(custom_path)
    backup_dir = resolve_backup_dir(custom_path)
    ensure_data_dir(data_path)
    return JsonStorage(data_path, backup_dir=backup_dir)


# ---- 命令处理函数 ----

def handle_create(args: list[str]) -> None:
    """处理 create 命令."""
    params = _parse_kwargs(args)
    title = params.get("--title", params.get("-t", ""))
    if not title:
        print(colorize("错误: --title 是必填参数", "red"))
        sys.exit(1)
    ticket = create_ticket(
        _get_storage(params.get("--data-dir")),
        title=title,
        description=params.get("--desc", params.get("-d", "")),
        priority=params.get("--priority", params.get("-p", "medium")),
        status=params.get("--status", params.get("-s", "open")),
        assignee=params.get("--assignee", params.get("-a", "")),
        creator=params.get("--creator", params.get("-c", "")),
        tags=_parse_list(params.get("--tags")),
        due_date=params.get("--due-date"),
        estimated_hours=_parse_float(params.get("--hours")),
    )
    print(colorize(f"✓ 工单创建成功: {ticket.id}", "green"))
    _print_ticket(ticket)


def handle_list(args: list[str]) -> None:
    """处理 list 命令."""
    params = _parse_kwargs(args)
    tickets, total = list_tickets(
        _get_storage(params.get("--data-dir")),
        status=params.get("--status"),
        priority=params.get("--priority"),
        assignee=params.get("--assignee"),
        tag=params.get("--tag"),
        search=params.get("--search"),
        sort_by=params.get("--sort", "created_at"),
        sort_desc=params.get("--order", "desc") != "asc",
        page=int(params.get("--page", "1")),
        page_size=int(params.get("--page-size", "50")),
    )
    print_header(f"工单列表 (共 {total} 条)")
    if not tickets:
        print("  (无匹配工单)")
        return
    for t in tickets:
        _print_ticket_compact(t)
    print(f"\n共 {len(tickets)}/{total} 条")


def handle_view(args: list[str]) -> None:
    """处理 view 命令."""
    params = _parse_kwargs(args)
    ticket_id = params.get("--id", params.get("-i", ""))
    if not ticket_id:
        print(colorize("错误: --id 是必填参数", "red"))
        sys.exit(1)
    ticket = get_ticket(_get_storage(params.get("--data-dir")), ticket_id)
    if not ticket:
        print(colorize(f"工单不存在: {ticket_id}", "red"))
        sys.exit(1)
    print_header(f"工单详情: {ticket.id}")
    _print_ticket(ticket)


def handle_update(args: list[str]) -> None:
    """处理 update 命令."""
    params = _parse_kwargs(args)
    ticket_id = params.get("--id", params.get("-i", ""))
    if not ticket_id:
        print(colorize("错误: --id 是必填参数", "red"))
        sys.exit(1)
    kwargs = {}
    if "--status" in params:
        kwargs["status"] = params["--status"]
    if "--priority" in params:
        kwargs["priority"] = params["--priority"]
    if "--title" in params:
        kwargs["title"] = params["--title"]
    if "--desc" in params:
        kwargs["description"] = params["--desc"]
    if "--tags" in params:
        kwargs["tags"] = _parse_list(params["--tags"])
    if not kwargs:
        print(colorize("没有提供要更新的字段", "yellow"))
        return
    ticket = update_ticket(_get_storage(params.get("--data-dir")), ticket_id, **kwargs)
    if not ticket:
        print(colorize(f"工单不存在: {ticket_id}", "red"))
        sys.exit(1)
    print(colorize(f"✓ 工单 {ticket.id} 更新成功", "green"))
    _print_ticket(ticket)


def handle_assign(args: list[str]) -> None:
    """处理 assign 命令."""
    params = _parse_kwargs(args)
    ticket_id = params.get("--id", params.get("-i", ""))
    assignee = params.get("--to", params.get("-t", ""))
    if not ticket_id or not assignee:
        print(colorize("错误: --id 和 --to 是必填参数", "red"))
        sys.exit(1)
    ticket = assign_ticket(_get_storage(params.get("--data-dir")), ticket_id, assignee)
    if not ticket:
        print(colorize(f"工单不存在: {ticket_id}", "red"))
        sys.exit(1)
    print(colorize(f"✓ 工单 {ticket.id} 已指派给 {assignee}", "green"))
    _print_ticket(ticket)


def handle_comment(args: list[str]) -> None:
    """处理 comment 命令."""
    params = _parse_kwargs(args)
    ticket_id = params.get("--id", params.get("-i", ""))
    msg = params.get("--msg", params.get("-m", ""))
    author = params.get("--author", params.get("-a", "匿名"))
    if not ticket_id or not msg:
        print(colorize("错误: --id 和 --msg 是必填参数", "red"))
        sys.exit(1)
    comment = add_comment(_get_storage(params.get("--data-dir")), ticket_id, author, msg)
    if not comment:
        print(colorize(f"工单不存在: {ticket_id}", "red"))
        sys.exit(1)
    print(colorize(f"✓ 评论已添加到 {ticket_id}", "green"))
    print(f"   [{comment['created_at']}] {comment['author']}: {comment['message']}")


def handle_stats(args: list[str]) -> None:
    """处理 stats 命令."""
    params = _parse_kwargs(args)
    stats = get_ticket_stats(_get_storage(params.get("--data-dir")))
    print_header("工单统计")
    print(f"  工单总数: {stats['total']}")
    print()
    print("  按状态分布:")
    for status in VALID_STATUSES:
        count = stats["status_counts"].get(status, 0)
        bar = _bar(count, max(stats["status_counts"].values(), default=1))
        print(f"    {status:12s}: {count:3d} {bar}")
    print()
    print("  按优先级分布:")
    for pri in VALID_PRIORITIES:
        count = stats["priority_counts"].get(pri, 0)
        bar = _bar(count, max(stats["priority_counts"].values(), default=1))
        print(f"    {pri:8s}: {count:3d} {bar}")
    print()
    print("  每人任务数:")
    for person, count in sorted(stats["assignee_counts"].items(), key=lambda x: -x[1]):
        bar = _bar(count, max(stats["assignee_counts"].values(), default=1))
        print(f"    {person:12s}: {count:3d} {bar}")
    print()
    if stats["overdue_count"]:
        print(colorize(f"  ⚠ 超期工单: {stats['overdue_count']}", "yellow"))
    else:
        print(f"  超期工单: 0")


def handle_board(args: list[str]) -> None:
    """处理 board 命令 — 打印文本看板."""
    params = _parse_kwargs(args)
    board = generate_kanban_board(_get_storage(params.get("--data-dir")))
    print_header("工单看板 (文本版)")
    column_names = {
        "open": "待处理",
        "in_progress": "进行中",
        "review": "评审中",
        "done": "已完成",
        "closed": "已关闭",
    }
    for status_key, display_name in column_names.items():
        tickets = board.get(status_key, [])
        print()
        title = f" {display_name} ({status_key}) [{len(tickets)}] "
        print(colorize(f"┌{'─' * 58}┐", "cyan"))
        print(colorize(f"│{title:^58}│", "cyan"))
        print(colorize(f"└{'─' * 58}┘", "cyan"))
        if not tickets:
            print("    (空)")
            continue
        for t in tickets:
            pri_color = _priority_color(t.priority)
            print(
                f"  {colorize(t.id, 'bold')} "
                f"{colorize(f'[{t.priority}]', pri_color)} "
                f"{t.title[:40]}"
            )
            if t.assignee:
                print(f"    → 负责人: {t.assignee}")
            if t.due_date:
                overdue = " ⚠ 超期" if t.is_overdue else ""
                print(f"    → 截止: {t.due_date}{overdue}")
        print()


def handle_backup(args: list[str]) -> None:
    """处理 backup 命令."""
    params = _parse_kwargs(args)
    suffix = params.get("--suffix")
    storage = _get_storage(params.get("--data-dir"))
    try:
        path = storage.backup(suffix)
        print(colorize(f"✓ 备份成功: {path}", "green"))
    except FileNotFoundError as e:
        print(colorize(f"错误: {e}", "red"))
        sys.exit(1)


# ---- 辅助函数 ----

def _parse_kwargs(args: list[str]) -> dict[str, str]:
    """将 CLI args 解析为 key-value 字典."""
    params: dict[str, str] = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                params[key] = args[i + 1]
                i += 2
            else:
                params[key] = ""
                i += 1
        else:
            i += 1
    return params


def _parse_list(value: Optional[str]) -> list[str]:
    """解析逗号分隔的标签列表."""
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _print_ticket(ticket: Ticket) -> None:
    """详细打印工单."""
    pri_color = _priority_color(ticket.priority)
    print(f"  ID:          {colorize(ticket.id, 'bold')}")
    print(f"  标题:        {ticket.title}")
    print(f"  描述:        {ticket.description or '(无描述)'}")
    print(f"  状态:        {ticket.status}")
    print(f"  优先级:      {colorize(f'[{ticket.priority}]', pri_color)}")
    print(f"  负责人:      {ticket.assignee or '未指派'}")
    print(f"  创建人:      {ticket.creator or '匿名'}")
    print(f"  创建时间:    {ticket.created_at}")
    print(f"  更新时间:    {ticket.updated_at}")
    if ticket.tags:
        print(f"  标签:        {', '.join(ticket.tags)}")
    if ticket.due_date:
        overdue = " ⚠ 已超期" if ticket.is_overdue else ""
        print(f"  截止日期:    {ticket.due_date}{overdue}")
    if ticket.estimated_hours is not None:
        print(f"  预估工时:    {ticket.estimated_hours}h")
    if ticket.comments:
        print(f"  评论 ({len(ticket.comments)}):")
        for c in ticket.comments:
            print(f"    [{c['created_at']}] {c['author']}: {c['message']}")
    print()


def _print_ticket_compact(ticket: Ticket) -> None:
    """简洁打印工单（列表模式）."""
    pri_color = _priority_color(ticket.priority)
    overdue = " ⚠" if ticket.is_overdue else ""
    print(
        f"  {colorize(ticket.id, 'bold'):12s} "
        f"{colorize(f'[{ticket.priority}]', pri_color):10s} "
        f"{ticket.status:12s} "
        f"{ticket.title[:35]:35s} "
        f"{ticket.assignee or '-':10s}"
        f"{overdue}"
    )


def _priority_color(priority: str) -> str:
    return {
        "critical": "red",
        "high": "yellow",
        "medium": "blue",
        "low": "green",
    }.get(priority, "white")


def _bar(count: int, max_count: int, width: int = 20) -> str:
    """生成简单的文本进度条."""
    if max_count == 0:
        return "█" * 0
    filled = int(count / max_count * width)
    return "█" * filled + "░" * (width - filled)
