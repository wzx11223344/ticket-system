# Ticket Management System (TMS)

![CI](https://github.com/your-org/ticket-system/actions/workflows/ci.yml/badge.svg)

**实战级轻量化工单/Task管理系统** — 灵感源自 Jira / 飞书，但轻量到只需一个 `python app.py` 即可运行。

---

## 功能特性

- **CLI 模式** — 终端高效管理工单，适合开发者和运维人员
- **Web 看板** — 可视化看板 + 图表统计，适合团队协作
- **拖拽操作** — 看板支持拖拽改变工单状态
- **灵活筛选** — 按状态、优先级、负责人、关键词筛选
- **完整生命周期** — open → in_progress → review → done → closed
- **JSON 存储** — 零外部数据库依赖，自动备份与恢复
- **REST API** — 完整的 RESTful 接口，方便集成

---

## 快速开始

### 安装

```bash
# 1. 克隆项目
git clone https://github.com/your-org/ticket-system.git
cd ticket-system

# 2. 安装依赖
pip install -r requirements.txt

# 3. 直接使用（数据自动创建在 data/ 目录）
python app.py list
```

### CLI 使用

```bash
# 创建工单
python app.py create --title "修复登录Bug" --desc "用户反馈无法登录" --priority high --assignee 张三

# 列出工单
python app.py list
python app.py list --status open
python app.py list --priority high

# 查看详情
python app.py view --id TKT-0001

# 更新工单
python app.py update --id TKT-0001 --status in_progress

# 重新指派
python app.py assign --id TKT-0001 --to 李四

# 添加评论
python app.py comment --id TKT-0001 --msg "已修复，等待验证"

# 查看统计
python app.py stats

# 文本版看板
python app.py board

# 备份数据
python app.py backup
```

### Web 看板

```bash
python app.py web
```

然后打开浏览器访问 **http://127.0.0.1:5000**

Web 看板提供:
- 五列看板视图（待处理 / 进行中 / 评审中 / 已完成 / 已关闭）
- 拖拽改变工单状态
- 搜索与筛选
- 状态分布饼图 / 优先级柱状图 / 每人任务数
- 新建工单表单
- 工单详情弹窗（含评论、指派、状态更新）

---

## REST API

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/tickets` | 工单列表（支持 `?status=open&priority=high&search=xxx`） |
| POST | `/api/tickets` | 创建工单 |
| GET | `/api/tickets/<id>` | 工单详情 |
| PUT | `/api/tickets/<id>` | 更新工单 |
| POST | `/api/tickets/<id>/comments` | 添加评论 |
| POST | `/api/tickets/<id>/assign` | 指派 |
| GET | `/api/stats` | 统计信息 |
| GET | `/api/board` | 看板数据 |

---

## 项目结构

```
ticket-system/
├── tms/                    # 核心包
│   ├── core.py             # 工单核心模型与逻辑
│   ├── cli_handler.py      # CLI 命令处理
│   ├── db.py               # JSON 数据库层
│   ├── api.py              # Flask REST API
│   └── utils.py            # 工具函数
├── templates/
│   └── kanban.html         # 看板页面
├── app.py                  # CLI + Web 双模式入口
├── tests/                  # 单元测试
├── requirements.txt
├── pyproject.toml
├── .github/workflows/ci.yml
└── README.md
```

---

## 运行测试

```bash
pip install pytest flake8
pytest tests/ -v
flake8 tms/ tests/ app.py --max-line-length=100
```

---

## 配置

通过环境变量 `TMS_DATA_DIR` 可自定义数据存储目录:

```bash
export TMS_DATA_DIR=/path/to/data
python app.py list
```

---

## License

MIT
