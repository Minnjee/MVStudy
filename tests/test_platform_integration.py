"""票 01 验收：从空结构迁移 → 登录 → 身份 → 班级范围。

全部走隔离的 PostgreSQL 库，不使用 create_all()，不以 SQLite 替代。
运行：python -m unittest discover -s tests
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from mvstudy.app import create_app
from mvstudy.db import build_engine, build_session_factory
from mvstudy.domains.platform.seed import seed

TEST_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://mvstudy:mvstudy@127.0.0.1:5433/mvstudy_test",
)

STUDENT = {"login": "s01", "password": "Stud@123"}
TEACHER = {"login": "t01", "password": "Teach@123"}
ADMIN = {"login": "a01", "password": "Admin@123"}


def alembic_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", TEST_URL)
    return config


def run_sql(statement: str, params: dict | None = None) -> None:
    engine = build_engine(TEST_URL)
    try:
        with engine.begin() as connection:
            connection.execute(text(statement), params or {})
    finally:
        engine.dispose()


class PlatformTicketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.previous_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = TEST_URL
        run_sql("DROP SCHEMA IF EXISTS public CASCADE")
        run_sql("CREATE SCHEMA public")
        command.upgrade(alembic_config(), "head")
        session = build_session_factory(build_engine(TEST_URL))()
        try:
            seed(session)
        finally:
            session.close()
        cls.app = create_app({"DATABASE_URL": TEST_URL, "TESTING": True})

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = cls.previous_url

    def client(self):
        return self.app.test_client()

    def login(self, account: dict) -> str:
        response = self.client().post("/api/login", json=account)
        self.assertEqual(response.status_code, 200, response.json)
        return response.json["access_token"]

    def auth(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def set_enabled(self, user_id: str, enabled: bool) -> None:
        run_sql("UPDATE users SET enabled = :enabled WHERE user_id = :uid", {"enabled": enabled, "uid": user_id})

    def test_login_issues_token_and_me_reads_database(self):
        client = self.client()
        token = self.login(STUDENT)

        me = client.get("/api/me", headers=self.auth(token))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json["user_id"], "u-s01")
        self.assertEqual(me.json["role_id"], "student")
        self.assertEqual(me.json["classes"], [{"class_id": "c1", "relation": "student"}])

        # 直接改库后同一凭证立即看到新值：授权来自数据库，不是 token 里的快照。
        run_sql("UPDATE users SET display_name = :name WHERE user_id = :uid", {"name": "李同学（改）", "uid": "u-s01"})
        try:
            self.assertEqual(client.get("/api/me", headers=self.auth(token)).json["display_name"], "李同学（改）")
        finally:
            run_sql("UPDATE users SET display_name = :name WHERE user_id = :uid", {"name": "李同学", "uid": "u-s01"})

    def test_wrong_password_and_missing_credentials(self):
        client = self.client()
        self.assertEqual(client.post("/api/login", json={"login": "s01", "password": "wrong"}).status_code, 401)
        self.assertEqual(client.post("/api/login", json={"login": "nobody", "password": "Stud@123"}).status_code, 401)
        self.assertEqual(client.get("/api/me").status_code, 401)
        self.assertEqual(client.get("/api/me", headers=self.auth("forged.token.value")).status_code, 401)

    def test_disabled_account_loses_access_on_next_request(self):
        client = self.client()
        token = self.login(STUDENT)
        self.assertEqual(client.get("/api/me", headers=self.auth(token)).status_code, 200)

        self.set_enabled("u-s01", False)
        try:
            self.assertEqual(client.get("/api/me", headers=self.auth(token)).status_code, 401)
            self.assertEqual(client.post("/api/login", json=STUDENT).status_code, 401)
        finally:
            self.set_enabled("u-s01", True)

        self.assertEqual(client.get("/api/me", headers=self.auth(token)).status_code, 200)

    def test_student_cannot_read_other_class_roster(self):
        token = self.login(STUDENT)
        response = self.client().get("/api/classes/c2/members", headers=self.auth(token))
        self.assertEqual(response.status_code, 404)

    def test_student_has_no_roster_access_even_for_own_class(self):
        # U5 调用方为 4 号、8 号与管理页；学生不在授权范围，按 not_found 处理。
        token = self.login(STUDENT)
        self.assertEqual(self.client().get("/api/classes/c1/members", headers=self.auth(token)).status_code, 404)

    def test_teacher_is_limited_to_classes_they_teach(self):
        token = self.login(TEACHER)
        client = self.client()
        own = client.get("/api/classes/c1/members", headers=self.auth(token))
        self.assertEqual(own.status_code, 200)
        relations = {item["relation"] for item in own.json["items"]}
        self.assertEqual(relations, {"teacher", "student"})
        self.assertEqual(client.get("/api/classes/c2/members", headers=self.auth(token)).status_code, 404)

    def test_admin_can_read_any_class(self):
        token = self.login(ADMIN)
        self.assertEqual(self.client().get("/api/classes/c2/members", headers=self.auth(token)).status_code, 200)

    def test_relation_filter_narrows_roster(self):
        token = self.login(TEACHER)
        response = self.client().get("/api/classes/c1/members?relation=teacher", headers=self.auth(token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["user_id"] for item in response.json["items"]], ["u-t01"])

    def test_second_upgrade_keeps_existing_accounts(self):
        command.upgrade(alembic_config(), "head")
        self.assertEqual(self.client().post("/api/login", json=STUDENT).status_code, 200)

    def test_each_method_and_path_has_one_handler(self):
        seen: dict[tuple[str, str], str] = {}
        for rule in self.app.url_map.iter_rules():
            for method in rule.methods - {"HEAD", "OPTIONS"}:
                key = (method, rule.rule)
                self.assertNotIn(key, seen, f"{key} 被多个处理器提供")
                seen[key] = rule.endpoint


if __name__ == "__main__":
    unittest.main()
