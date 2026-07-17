"""Flask REST API — 工单系统的 Web 接口."""

import os
import sys
from typing import Optional

from flask import Flask, jsonify, request, render_template, send_from_directory

from tms.core import (
    create_ticket,
    update_ticket,
    assign_ticket,
    add_comment,
    get_ticket,
    list_tickets,
    get_ticket_stats,
    generate_kanban_board,
)
from tms.db import JsonStorage
from tms.utils import resolve_storage_path, resolve_backup_dir, ensure_data_dir


def create_app(data_dir: Optional[str] = None) -> Flask:
    """创建并配置 Flask 应用."""
    app = Flask(
        __name__,
        template_folder=_resolve_template_dir(),
        static_folder=None,
    )
    _init_storage(app, data_dir)

    # ---- 注册路由 ----

    @app.route("/")
    def index():
        return render_template("kanban.html")

    @app.route("/api/tickets", methods=["GET", "POST"])
    def tickets():
        storage = _get_storage(app)
        if request.method == "POST":
            data = request.get_json(force=True, silent=True) or {}
            ticket = create_ticket(
                storage,
                title=data.get("title", ""),
                description=data.get("description", ""),
                priority=data.get("priority", "medium"),
                status=data.get("status", "open"),
                assignee=data.get("assignee", ""),
                creator=data.get("creator", ""),
                tags=data.get("tags"),
                due_date=data.get("due_date"),
                estimated_hours=_safe_float(data.get("estimated_hours")),
            )
            return jsonify(ticket.to_dict()), 201

        # GET 参数
        tickets_list, total = list_tickets(
            storage,
            status=request.args.get("status"),
            priority=request.args.get("priority"),
            assignee=request.args.get("assignee"),
            tag=request.args.get("tag"),
            search=request.args.get("search"),
            sort_by=request.args.get("sort_by", "created_at"),
            sort_desc=request.args.get("sort_desc", "true").lower() != "false",
            page=int(request.args.get("page", 1)),
            page_size=int(request.args.get("page_size", 200)),
        )
        return jsonify({
            "tickets": [t.to_dict() for t in tickets_list],
            "total": total,
        })

    @app.route("/api/tickets/<ticket_id>", methods=["GET", "PUT"])
    def ticket_detail(ticket_id):
        storage = _get_storage(app)
        if request.method == "PUT":
            data = request.get_json(force=True, silent=True) or {}
            ticket = update_ticket(storage, ticket_id, **data)
            if not ticket:
                return jsonify({"error": "工单不存在"}), 404
            return jsonify(ticket.to_dict())
        ticket = get_ticket(storage, ticket_id)
        if not ticket:
            return jsonify({"error": "工单不存在"}), 404
        return jsonify(ticket.to_dict())

    @app.route("/api/tickets/<ticket_id>/comments", methods=["POST"])
    def ticket_comment(ticket_id):
        storage = _get_storage(app)
        data = request.get_json(force=True, silent=True) or {}
        comment = add_comment(
            storage,
            ticket_id,
            author=data.get("author", "匿名"),
            message=data.get("message", ""),
        )
        if not comment:
            return jsonify({"error": "工单不存在"}), 404
        return jsonify(comment), 201

    @app.route("/api/stats")
    def stats():
        storage = _get_storage(app)
        return jsonify(get_ticket_stats(storage))

    @app.route("/api/board")
    def board():
        storage = _get_storage(app)
        raw = generate_kanban_board(storage)
        return jsonify({
            status: [t.to_dict() for t in tickets]
            for status, tickets in raw.items()
        })

    @app.route("/api/tickets/<ticket_id>/assign", methods=["POST"])
    def ticket_assign_route(ticket_id):
        storage = _get_storage(app)
        data = request.get_json(force=True, silent=True) or {}
        assignee = data.get("assignee", "")
        if not assignee:
            return jsonify({"error": "缺少 assignee 字段"}), 400
        ticket = assign_ticket(storage, ticket_id, assignee)
        if not ticket:
            return jsonify({"error": "工单不存在"}), 404
        return jsonify(ticket.to_dict())

    return app


def _init_storage(app: Flask, data_dir: Optional[str] = None) -> None:
    """初始化存储路径并存入 app config."""
    data_path = resolve_storage_path(data_dir)
    backup_dir = resolve_backup_dir(data_dir)
    ensure_data_dir(data_path)
    app.config["STORAGE_PATH"] = data_path
    app.config["BACKUP_DIR"] = backup_dir


def _get_storage(app: Flask) -> JsonStorage:
    return JsonStorage(
        app.config["STORAGE_PATH"],
        backup_dir=app.config.get("BACKUP_DIR", ""),
    )


def _resolve_template_dir() -> str:
    """确定 templates 目录的绝对路径."""
    # 如果作为包运行，模板在项目根目录下
    current = os.path.dirname(os.path.abspath(__file__))  # .../tms/
    project_root = os.path.dirname(current)  # .../ticket-system/
    template_dir = os.path.join(project_root, "templates")
    if os.path.isdir(template_dir):
        return template_dir
    # 回退
    return os.path.join(os.getcwd(), "templates")


def _safe_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def run_web_server(data_dir: Optional[str] = None, host: str = "127.0.0.1", port: int = 5000, debug: bool = True) -> None:
    """启动 Web 服务器."""
    app = create_app(data_dir)
    print(f"  Ticket Management System - Web 看板")
    print(f"  {'=' * 40}")
    print(f"  地址: http://{host}:{port}")
    print(f"  API:  http://{host}:{port}/api/tickets")
    print(f"  {'=' * 40}")
    app.run(host=host, port=port, debug=debug)
