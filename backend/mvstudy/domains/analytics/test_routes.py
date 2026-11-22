"""E2/E3 HTTP 契约测试：统计口径、权限边界、区间校验与周报可复算。"""
from __future__ import annotations

import json
import unittest

from flask import g

from .routes import _actor, create_analytics_demo

FROM = "2026-11-16T00:00:00+08:00"
TO = "2026-11-23T00:00:00+08:00"

TEACHER_C1 = {"user_id": "t1", "role_id": "teacher", "permissions": [],
              "classes": [{"class_id": "c1", "relation": "teacher"}]}
STUDENT = {"user_id": "u1", "role_id": "student", "permissions": [],
           "classes": [{"class_id": "c1", "relation": "student"}]}
ADMIN_FULL = {"user_id": "a1", "role_id": "admin", "permissions": ["analytics.read"]}
ADMIN_LIMITED = {"user_id": "a2", "role_id": "admin", "permissions": []}


def head(actor: dict) -> dict[str, str]:
    return {"X-Actor": json.dumps(actor, ensure_ascii=False)}


class AnalyticsRoutesTest(unittest.TestCase):
    def setUp(self):
        self.client = create_analytics_demo().test_client()

    def e2(self, class_id="c1", actor=TEACHER_C1, query=None):
        params = {"from": FROM, "to": TO} if query is None else query
        return self.client.get(f"/api/classes/{class_id}/analytics",
                               query_string=params, headers=head(actor))

    def test_e2_contract_and_acceptance_sample(self):
        resp = self.e2()
        self.assertEqual(resp.status_code, 200)
        data = resp.json
        for key in ("class_id", "as_of", "submitted_pairs", "assigned_pairs",
                    "completion_rate", "run_success_rate", "top_topics", "weekly", "scores"):
            self.assertIn(key, data)
        self.assertEqual(data["class_id"], "c1")
        self.assertEqual(data["assigned_pairs"], 4)
        self.assertEqual(data["submitted_pairs"], 2)
        self.assertEqual(data["completion_rate"], 0.5)
        self.assertAlmostEqual(data["run_success_rate"], 2 / 3)
        self.assertEqual(data["top_topics"], [{"topic": "阈值", "count": 2}, {"topic": "边缘检测", "count": 1}])
        self.assertEqual(data["weekly"], [{"week": "2026-11-16", "submitted_pairs": 2, "assigned_pairs": 4}])

    def test_switch_class_recomputes_and_empty_denominator(self):
        other = self.e2("c2", actor=ADMIN_FULL).json
        self.assertEqual(other["assigned_pairs"], 3)
        self.assertEqual(other["submitted_pairs"], 1)
        self.assertAlmostEqual(other["completion_rate"], 1 / 3)
        empty = self.e2("c3", actor=ADMIN_FULL).json
        self.assertEqual(empty["assigned_pairs"], 0)
        self.assertIsNone(empty["completion_rate"])
        self.assertEqual(empty["top_topics"], [])

    def test_permission_boundaries(self):
        self.assertEqual(self.e2(actor=STUDENT).status_code, 403)
        self.assertEqual(self.e2(actor=ADMIN_LIMITED).status_code, 403)
        self.assertEqual(self.e2("c2", actor=TEACHER_C1).status_code, 404)
        self.assertEqual(self.e2(actor={}).status_code, 401)
        self.assertEqual(self.client.get(f"/api/classes/c1/analytics",
                                         query_string={"from": FROM, "to": TO}).status_code, 401)
        self.assertEqual(self.e2(actor=ADMIN_FULL).status_code, 200)

    def test_invalid_range(self):
        for params in ({"from": FROM}, {"to": TO}, {"from": TO, "to": FROM},
                       {"from": "2026-11-16", "to": TO},
                       {"from": "bad", "to": TO}):
            with self.subTest(params=params):
                self.assertEqual(self.e2(query=params).status_code, 400)

    def test_e3_weekly_report_is_recomputable(self):
        resp = self.client.post("/api/classes/c1/weekly-report",
                                json={"from": FROM, "to": TO}, headers=head(TEACHER_C1))
        self.assertEqual(resp.status_code, 200)
        report = resp.json
        self.assertEqual(report["from"], FROM)
        self.assertEqual(report["to"], TO)
        self.assertEqual(report["summary"], "4 个应交名额中已有 2 个提交。")
        self.assertTrue(report["suggestions"])
        self.assertEqual(report["metrics"]["completion_rate"], 0.5)
        self.assertEqual(report["as_of"], report["metrics"]["as_of"])

    def test_e3_permission_and_range(self):
        url = "/api/classes/c1/weekly-report"
        self.assertEqual(self.client.post(url, json={"from": FROM, "to": TO}, headers=head(STUDENT)).status_code, 403)
        self.assertEqual(self.client.post(url, json={"from": TO, "to": FROM}, headers=head(TEACHER_C1)).status_code, 400)
        self.assertEqual(self.client.post(url, data="not json", headers=head(TEACHER_C1)).status_code, 400)

    def test_host_actor_takes_priority_over_header(self):
        app = create_analytics_demo()
        with app.test_request_context(headers=head(STUDENT)):
            g.current_actor = ADMIN_FULL
            self.assertEqual(_actor()["role_id"], "admin")


if __name__ == "__main__":
    unittest.main()
