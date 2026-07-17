"""测试数据库层 — tms.db."""

import json
import os
import tempfile
import pytest

from tms.db import JsonStorage


@pytest.fixture
def storage():
    """创建临时 JSON 存储."""
    tmp = tempfile.mktemp(suffix=".json")
    backup_dir = tempfile.mkdtemp()
    store = JsonStorage(tmp, backup_dir=backup_dir)
    yield store
    if os.path.exists(tmp):
        os.remove(tmp)
    if os.path.isdir(backup_dir):
        import shutil
        shutil.rmtree(backup_dir)


class TestJsonStorage:
    def test_save_and_load(self, storage):
        """测试保存并加载数据."""
        data = {
            "TKT-001": {"id": "TKT-001", "title": "测试工单", "status": "open"},
            "TKT-002": {"id": "TKT-002", "title": "另一个工单", "status": "done"},
        }
        storage.save(data)
        loaded = storage.load()
        assert len(loaded) == 2
        assert loaded["TKT-001"]["title"] == "测试工单"
        assert loaded["TKT-002"]["status"] == "done"

    def test_load_empty_file(self, storage):
        """测试文件不存在时返回空字典."""
        data = storage.load()
        assert data == {}

    def test_overwrite_existing_data(self, storage):
        """测试覆盖写入已有文件."""
        storage.save({"TKT-001": {"title": "原始"}})
        storage.save({"TKT-002": {"title": "新工单"}})
        loaded = storage.load()
        assert "TKT-001" not in loaded  # 完全被覆盖
        assert loaded["TKT-002"]["title"] == "新工单"

    def test_save_large_dataset(self, storage):
        """测试大量数据的保存和加载."""
        data = {}
        for i in range(100):
            tid = f"TKT-{i:04d}"
            data[tid] = {"id": tid, "title": f"工单{i}", "index": i}
        storage.save(data)
        loaded = storage.load()
        assert len(loaded) == 100
        assert loaded["TKT-0050"]["index"] == 50

    def test_backup_and_restore(self, storage):
        """测试备份和恢复."""
        original = {"TKT-001": {"title": "备份测试"}}
        storage.save(original)

        # 备份
        backup_path = storage.backup("test_backup")
        assert os.path.exists(backup_path)

        # 修改原数据
        storage.save({"TKT-002": {"title": "新数据"}})

        # 恢复
        storage.restore(backup_path)
        restored = storage.load()
        assert "TKT-001" in restored
        assert restored["TKT-001"]["title"] == "备份测试"
        assert "TKT-002" not in restored

    def test_list_backups(self, storage):
        """测试列出备份文件."""
        data = {"TKT-001": {"title": "测试"}}
        storage.save(data)

        storage.backup("v1")
        storage.backup("v2")

        backups = storage.list_backups()
        assert len(backups) == 2
