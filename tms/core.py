"""工单核心模型与业务逻辑."""

import uuid
from datetime import datetime, timezone
from typing import Optional


TICKET_ID_PREFIX = "TKT"

VALID_STATUSES = ("open", "in_progress", "review", "done", "closed")
VALID_PRIORITIES = ("low", "medium", "high", "critical")


def _now() -> str:
    """返回 ISO 格式的 UTC 时间字符串."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _generate_ticket_id(counter: int) -> str:
    """根据内部计数器生成 TKT-001 格式的工单 ID."""
    return f"{TICKET_ID_PREFIX}-{counter:04d}"


class Ticket:
    """工单模型."""

    __slots__ = (
        "id", "title", "description", "status", "priority",
        "assignee", "creator", "created_at", "updated_at",
        "comments", "tags", "due_date", "estimated_hours",
    )

    def __init__(
        self,
        title: str,
        description: str = "",
        status: str = "open",
        priority: str = "medium",
        assignee: str = "",
        creator: str = "",
        tags: Optional[list[str]] = None,
        due_date: Optional[str] = None,
        estimated_hours: Optional[float] = None,
        ticket_id: Optional[str] = None,
        created_at: Optional[str] = None,
        comments: Optional[list[dict]] = None,
    ):
        # id 在外部通过工厂方法设置
        self.id: str = ticket_id or ""
        self.title: str = title.strip()
        self.description: str = description.strip()
        self.status: str = status if status in VALID_STATUSES else "open"
        self.priority: str = priority if priority in VALID_PRIORITIES else "medium"
        self.assignee: str = assignee.strip()
        self.creator: str = creator.strip()
        self.created_at: str = created_at or _now()
        self.updated_at: str = _now()
        self.comments: list[dict] = comments or []
        self.tags: list[str] = tags or []
        self.due_date: Optional[str] = due_date
        self.estimated_hours: Optional[float] = estimated_hours

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assignee": self.assignee,
            "creator": self.creator,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "comments": self.comments,
            "tags": self.tags,
            "due_date": self.due_date,
            "estimated_hours": self.estimated_hours,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Ticket":
        return cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            status=data.get("status", "open"),
            priority=data.get("priority", "medium"),
            assignee=data.get("assignee", ""),
            creator=data.get("creator", ""),
            tags=data.get("tags", []),
            due_date=data.get("due_date"),
            estimated_hours=data.get("estimated_hours"),
            ticket_id=data.get("id", ""),
            created_at=data.get("created_at"),
            comments=data.get("comments", []),
        )

    def update(self, **kwargs) -> None:
        """更新工单字段，并自动刷新 updated_at."""
        allowed = {"title", "description", "status", "priority",
                   "assignee", "tags", "due_date", "estimated_hours"}
        for key, value in kwargs.items():
            if key in allowed:
                if key == "status" and value not in VALID_STATUSES:
                    continue
                if key == "priority" and value not in VALID_PRIORITIES:
                    continue
                setattr(self, key, value)
        self.updated_at = _now()

    def add_comment(self, author: str, message: str) -> dict:
        """添加评论，返回评论字典."""
        comment = {
            "id": str(uuid.uuid4())[:8],
            "author": author.strip(),
            "message": message.strip(),
            "created_at": _now(),
        }
        self.comments.append(comment)
        self.updated_at = _now()
        return comment

    # ---- 便捷属性 ----
    @property
    def is_overdue(self) -> bool:
        """是否已超期（有截止日期且已过期，且状态未结束)."""
        if not self.due_date or self.status in ("done", "closed"):
            return False
        try:
            due = datetime.fromisoformat(self.due_date)
            return due < datetime.now(due.tzinfo) if due.tzinfo else due < datetime.now()
        except (ValueError, TypeError):
            return False

    @property
    def age_hours(self) -> float:
        """工单存在时长（小时）."""
        try:
            created = datetime.fromisoformat(self.created_at)
            now = datetime.now(timezone.utc)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            return (now - created).total_seconds() / 3600
        except (ValueError, TypeError):
            return 0.0


# ===================================================================
# 核心业务函数
# ===================================================================

def create_ticket(
    storage: "BaseStorage",
    title: str,
    description: str = "",
    status: str = "open",
    priority: str = "medium",
    assignee: str = "",
    creator: str = "",
    tags: Optional[list[str]] = None,
    due_date: Optional[str] = None,
    estimated_hours: Optional[float] = None,
) -> Ticket:
    """创建工单并持久化."""
    tickets = storage.load()
    next_id = max((int(t.get("id", "TKT-0000").split("-")[1]) for t in tickets.values()), default=0) + 1
    ticket = Ticket(
        title=title,
        description=description,
        status=status,
        priority=priority,
        assignee=assignee,
        creator=creator,
        tags=tags or [],
        due_date=due_date,
        estimated_hours=estimated_hours,
        ticket_id=_generate_ticket_id(next_id),
    )
    tickets[ticket.id] = ticket.to_dict()
    storage.save(tickets)
    return ticket


def update_ticket(
    storage: "BaseStorage",
    ticket_id: str,
    **kwargs,
) -> Optional[Ticket]:
    """更新工单，返回更新后的 Ticket；不存在返回 None."""
    tickets = storage.load()
    raw = tickets.get(ticket_id)
    if not raw:
        return None
    ticket = Ticket.from_dict(raw)
    ticket.update(**kwargs)
    tickets[ticket_id] = ticket.to_dict()
    storage.save(tickets)
    return ticket


def assign_ticket(
    storage: "BaseStorage",
    ticket_id: str,
    assignee: str,
) -> Optional[Ticket]:
    """重新指派工单."""
    return update_ticket(storage, ticket_id, assignee=assignee)


def add_comment(
    storage: "BaseStorage",
    ticket_id: str,
    author: str,
    message: str,
) -> Optional[dict]:
    """为工单添加评论，返回评论字典；工单不存在返回 None."""
    tickets = storage.load()
    raw = tickets.get(ticket_id)
    if not raw:
        return None
    ticket = Ticket.from_dict(raw)
    comment = ticket.add_comment(author, message)
    tickets[ticket_id] = ticket.to_dict()
    storage.save(tickets)
    return comment


def get_ticket(
    storage: "BaseStorage",
    ticket_id: str,
) -> Optional[Ticket]:
    """获取单个工单详情."""
    tickets = storage.load()
    raw = tickets.get(ticket_id)
    return Ticket.from_dict(raw) if raw else None


def list_tickets(
    storage: "BaseStorage",
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_desc: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Ticket], int]:
    """筛选/排序/分页查询工单。

    返回 (tickets, total_count).
    """
    raw_list = list(storage.load().values())

    # ---- 筛选 ----
    if status:
        raw_list = [t for t in raw_list if t.get("status") == status]
    if priority:
        raw_list = [t for t in raw_list if t.get("priority") == priority]
    if assignee:
        raw_list = [t for t in raw_list if t.get("assignee") == assignee]
    if tag:
        raw_list = [t for t in raw_list if tag in t.get("tags", [])]
    if search:
        q = search.lower()
        raw_list = [
            t for t in raw_list
            if q in t.get("title", "").lower()
            or q in t.get("description", "").lower()
        ]

    # ---- 排序 ----
    reverse = sort_desc
    raw_list.sort(key=lambda t: t.get(sort_by, ""), reverse=reverse)

    total = len(raw_list)

    # ---- 分页 ----
    start = (page - 1) * page_size
    end = start + page_size
    page_data = raw_list[start:end]

    return [Ticket.from_dict(d) for d in page_data], total


def get_ticket_stats(storage: "BaseStorage") -> dict:
    """工单统计."""
    tickets = list(storage.load().values())

    status_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    assignee_counts: dict[str, int] = {}
    overdue_count = 0

    for raw in tickets:
        s = raw.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

        p = raw.get("priority", "unknown")
        priority_counts[p] = priority_counts.get(p, 0) + 1

        a = raw.get("assignee", "") or "未指派"
        assignee_counts[a] = assignee_counts.get(a, 0) + 1

        # 超期判断
        ticket = Ticket.from_dict(raw)
        if ticket.is_overdue:
            overdue_count += 1

    return {
        "total": len(tickets),
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "assignee_counts": assignee_counts,
        "overdue_count": overdue_count,
    }


def generate_kanban_board(storage: "BaseStorage") -> dict[str, list[Ticket]]:
    """生成看板数据结构：按状态分组."""
    tickets = [Ticket.from_dict(t) for t in storage.load().values()]
    board: dict[str, list[Ticket]] = {
        "open": [],
        "in_progress": [],
        "review": [],
        "done": [],
        "closed": [],
    }
    for t in tickets:
        col = t.status if t.status in board else "open"
        board[col].append(t)
    return board
