"""测试工单核心逻辑 — tms.core."""

import json
import os
import tempfile
import pytest

from tms.core import (
    Ticket,
    create_ticket,
    update_ticket,
    assign_ticket,
    add_comment,
    get_ticket,
    list_tickets,
    get_ticket_stats,
    generate_kanban_board,
    VALID_STATUSES,
)
from tms.db import JsonStorage


@pytest.fixture
def storage():
    """创建临时 JSON 文件作为存储."""
    tmp = tempfile.mktemp(suffix=".json")
    store = JsonStorage(tmp)
    yield store
    if os.path.exists(tmp):
        os.remove(tmp)


# ========== Ticket 模型测试 ==========

class TestTicketModel:
    def test_create_ticket_defaults(self):
        """测试创建工单时使用默认值."""
        t = Ticket(title="测试工单")
        assert t.title == "测试工单"
        assert t.status == "open"
        assert t.priority == "medium"
        assert t.assignee == ""
        assert t.comments == []
        assert t.tags == []

    def test_ticket_to_dict_from_dict_roundtrip(self):
        """测试序列化/反序列化双向转换."""
        original = Ticket(
            title="登录Bug",
            description="用户无法登录",
            status="in_progress",
            priority="high",
            assignee="张三",
            creator="李四",
            tags=["bug", "前端"],
            due_date="2026-08-01",
            estimated_hours=4.0,
        )
        original.id = "TKT-001"
        data = original.to_dict()
        restored = Ticket.from_dict(data)
        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.description == original.description
        assert restored.status == original.status
        assert restored.priority == original.priority
        assert restored.assignee == original.assignee
        assert restored.tags == original.tags

    def test_update_ticket_fields(self):
        """测试更新工单字段."""
        t = Ticket(title="原始标题")
        t.update(title="新标题", priority="high", status="in_progress")
        assert t.title == "新标题"
        assert t.priority == "high"
        assert t.status == "in_progress"

    def test_update_invalid_status_ignored(self):
        """测试设置非法状态被忽略."""
        t = Ticket(title="测试")
        t.update(status="nonexistent")
        assert t.status == "open"  # 保持原值

    def test_add_comment(self):
        """测试添加评论."""
        t = Ticket(title="测试")
        comment = t.add_comment("张三", "已修复")
        assert comment["author"] == "张三"
        assert comment["message"] == "已修复"
        assert len(t.comments) == 1

    def test_is_overdue(self):
        """测试超期判断."""
        t = Ticket(title="超期测试", due_date="2020-01-01")
        assert t.is_overdue is True
        t.status = "done"
        assert t.is_overdue is False  # 已完成的不算超期

    def test_age_hours(self):
        """测试工单存在时长."""
        import datetime
        from tms.core import _now
        t = Ticket(title="时长测试")
        assert t.age_hours >= 0


# ========== 核心业务函数测试 ==========

class TestCoreFunctions:
    def test_create_and_get_ticket(self, storage):
        """测试创建并获取工单."""
        ticket = create_ticket(
            storage,
            title="修复登录Bug",
            description="用户反馈无法登录",
            priority="high",
            assignee="张三",
        )
        assert ticket.id.startswith("TKT-")
        assert ticket.title == "修复登录Bug"

        fetched = get_ticket(storage, ticket.id)
        assert fetched is not None
        assert fetched.title == "修复登录Bug"

    def test_create_ticket_auto_increment_id(self, storage):
        """测试工单 ID 自动递增."""
        t1 = create_ticket(storage, title="工单1")
        t2 = create_ticket(storage, title="工单2")
        assert t1.id == "TKT-0001"
        assert t2.id == "TKT-0002"

    def test_update_ticket_status(self, storage):
        """测试更新工单状态."""
        ticket = create_ticket(storage, title="测试更新")
        updated = update_ticket(storage, ticket.id, status="in_progress")
        assert updated is not None
        assert updated.status == "in_progress"

    def test_update_nonexistent_ticket(self, storage):
        """测试更新不存在的工单返回 None."""
        result = update_ticket(storage, "TKT-9999", status="done")
        assert result is None

    def test_assign_ticket(self, storage):
        """测试指派工单."""
        ticket = create_ticket(storage, title="指派测试")
        assigned = assign_ticket(storage, ticket.id, "李四")
        assert assigned.assignee == "李四"

    def test_add_comment_to_ticket(self, storage):
        """测试为工单添加评论."""
        ticket = create_ticket(storage, title="评论测试")
        comment = add_comment(storage, ticket.id, "张三", "正在处理中")
        assert comment["message"] == "正在处理中"

        ticket_reloaded = get_ticket(storage, ticket.id)
        assert len(ticket_reloaded.comments) == 1

    def test_list_tickets_filter_by_status(self, storage):
        """测试按状态筛选工单."""
        create_ticket(storage, title="待处理工单", status="open")
        create_ticket(storage, title="进行中工单", status="in_progress")
        create_ticket(storage, title="已完成工单", status="done")

        results, total = list_tickets(storage, status="open")
        assert total == 1
        assert results[0].title == "待处理工单"

    def test_list_tickets_filter_by_priority(self, storage):
        """测试按优先级筛选."""
        create_ticket(storage, title="低优先级", priority="low")
        create_ticket(storage, title="高优先级", priority="high")
        create_ticket(storage, title="紧急", priority="critical")

        results, total = list_tickets(storage, priority="high")
        assert total == 1

    def test_list_tickets_search(self, storage):
        """测试按关键词搜索."""
        create_ticket(storage, title="登录页面Bug", description="用户无法登录")
        create_ticket(storage, title="注册功能开发", description="实现用户注册")

        results, total = list_tickets(storage, search="登录")
        assert total == 1

    def test_list_tickets_pagination(self, storage):
        """测试分页."""
        for i in range(5):
            create_ticket(storage, title=f"工单{i}")
        results, total = list_tickets(storage, page=1, page_size=2)
        assert len(results) == 2
        assert total == 5

    def test_get_ticket_stats(self, storage):
        """测试统计功能."""
        create_ticket(storage, title="紧急工单", priority="critical")
        create_ticket(storage, title="普通工单", priority="medium")
        create_ticket(storage, title="进行中", status="in_progress", assignee="张三")

        stats = get_ticket_stats(storage)
        assert stats["total"] == 3
        assert stats["status_counts"].get("open", 0) == 2
        assert stats["status_counts"].get("in_progress", 0) == 1
        assert "张三" in stats["assignee_counts"]

    def test_generate_kanban_board(self, storage):
        """测试看板生成."""
        create_ticket(storage, title="待处理1", status="open")
        create_ticket(storage, title="待处理2", status="open")
        create_ticket(storage, title="进行中", status="in_progress")
        create_ticket(storage, title="已完成", status="done")

        board = generate_kanban_board(storage)
        assert len(board["open"]) == 2
        assert len(board["in_progress"]) == 1
        assert len(board["done"]) == 1
        assert len(board["closed"]) == 0
