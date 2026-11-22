"""工单 08 的统计口径测试。

用工单约定的固定假数据验证：完成率、周一切换、问答重放、0 分与未批、
换班切换。运行方式：python -m pytest backend/mvstudy/domains/analytics/test_metrics.py
"""
import unittest

from mvstudy.domains.analytics.metrics import (
    build_analytics,
    build_weekly_report,
    completion_rate,
    run_success_rate,
    score_distribution,
    top_topics,
)

START = "2026-11-16T00:00:00+08:00"
END = "2026-11-23T00:00:00+08:00"
AS_OF = "2026-11-21T10:00:00+08:00"


def fixture():
    """4 人应交、2 人提交、其中 1 人重交；另有一班 c2 用于换班验证。"""
    recipients = [
        {"student_id": sid, "assignment_id": "a1", "published_at": "2026-11-16T09:00:00+08:00"}
        for sid in ("u1", "u2", "u3", "u4")
    ] + [
        {"student_id": "v1", "assignment_id": "a2", "published_at": "2026-11-16T09:00:00+08:00"}
    ]
    submissions = [
        {"submission_id": "s1", "student_id": "u1", "assignment_id": "a1", "revision": 1, "submitted_at": "2026-11-18T10:00:00+08:00"},
        {"submission_id": "s1b", "student_id": "u1", "assignment_id": "a1", "revision": 2, "submitted_at": "2026-11-19T10:00:00+08:00"},  # 重交
        {"submission_id": "s2", "student_id": "u2", "assignment_id": "a1", "revision": 1, "submitted_at": "2026-11-20T10:00:00+08:00"},
        {"submission_id": "s3", "student_id": "v1", "assignment_id": "a2", "revision": 1, "submitted_at": "2026-11-20T10:00:00+08:00"},
    ]
    runs = [
        {"run_id": "r1", "status": "succeeded"},
        {"run_id": "r2", "status": "failed"},
        {"run_id": "r3", "status": "queued"},  # 排队中不计入分母
    ]
    events = [
        {"type": "question.answered", "topic": "阈值"},
        {"type": "question.answered", "topic": "阈值"},
        {"type": "question.answered", "topic": "边缘检测"},
        {"type": "question.answered", "topic": None},  # 未分类
    ]
    grades = [
        {"submission_id": "s1b", "score": 95},  # u1 最新提交（重交版本）
    ]
    return recipients, submissions, runs, events, grades


class CompletionRateTest(unittest.TestCase):
    def test_four_assigned_two_submitted_one_resubmitted_is_half(self):
        recipients, submissions, _runs, _events, _grades = fixture()
        c1_recipients = [r for r in recipients if r["assignment_id"] == "a1"]
        c1_submissions = [s for s in submissions if s["assignment_id"] == "a1"]
        result = completion_rate(c1_recipients, c1_submissions, start=START, end=END, as_of=AS_OF)
        self.assertEqual(result["assigned_pairs"], 4)
        self.assertEqual(result["submitted_pairs"], 2)
        self.assertEqual(result["completion_rate"], 0.5)

    def test_zero_denominator_returns_none(self):
        result = completion_rate([], [], start=START, end=END, as_of=AS_OF)
        self.assertIsNone(result["completion_rate"])

    def test_submission_after_as_of_not_counted(self):
        recipients = [{"student_id": "u1", "assignment_id": "a1", "published_at": START}]
        submissions = [{"student_id": "u1", "assignment_id": "a1", "submitted_at": "2026-11-22T10:00:00+08:00"}]
        result = completion_rate(recipients, submissions, start=START, end=END, as_of=AS_OF)
        self.assertEqual(result["submitted_pairs"], 0)


class OtherMetricsTest(unittest.TestCase):
    def test_run_success_rate_ignores_queued(self):
        _r, _s, runs, _e, _g = fixture()
        self.assertEqual(run_success_rate(runs), 0.5)  # 1 成功 / (1成功+1失败)

    def test_top_topics_counts_only_questions_and_sorts_ties(self):
        _r, _s, _runs, events, _g = fixture()
        topics = top_topics(events)
        self.assertEqual(topics[0], {"topic": "阈值", "count": 2})
        self.assertEqual([t["topic"] for t in topics[1:]], ["未分类", "边缘检测"])

    def test_score_bands_include_zero_and_skip_ungraded(self):
        submissions = [
            {"student_id": "u1", "assignment_id": "a1", "revision": 1, "submission_id": "s1"},
            {"student_id": "u2", "assignment_id": "a1", "revision": 1, "submission_id": "s2"},
        ]
        grades = [{"submission_id": "s1", "score": 0}]  # 0 分要计入，s2 未批不计入
        result = score_distribution(submissions, grades)
        self.assertEqual(result[0], {"band": "<60", "count": 1})
        self.assertEqual(sum(item["count"] for item in result), 1)


class AnalyticsSnapshotTest(unittest.TestCase):
    def test_switch_class_switches_summary_and_metrics(self):
        recipients, submissions, runs, events, grades = fixture()
        c1 = build_analytics(
            class_id="c1",
            recipients=[r for r in recipients if r["assignment_id"] == "a1"],
            submissions=[s for s in submissions if s["assignment_id"] == "a1"],
            runs=runs, events=events, grades=grades,
            start=START, end=END, as_of=AS_OF,
        )
        c2 = build_analytics(
            class_id="c2",
            recipients=[r for r in recipients if r["assignment_id"] == "a2"],
            submissions=[s for s in submissions if s["assignment_id"] == "a2"],
            runs=runs, events=events, grades=grades,
            start=START, end=END, as_of=AS_OF,
        )
        self.assertEqual(c1["completion_rate"], 0.5)
        self.assertEqual(c2["completion_rate"], 1.0)  # 1 人应交 1 人提交
        report = build_weekly_report(c1)
        self.assertIn("2 个提交", report["summary"])
        self.assertEqual(report["metrics"], c1)  # 周报与 E2 同一快照

    def test_weekly_trend_uses_monday_key(self):
        recipients, submissions, runs, events, grades = fixture()
        result = build_analytics(
            class_id="c1",
            recipients=[r for r in recipients if r["assignment_id"] == "a1"],
            submissions=[s for s in submissions if s["assignment_id"] == "a1"],
            runs=runs, events=events, grades=grades,
            start=START, end=END, as_of=AS_OF,
        )
        self.assertTrue(all(row["week"] == "2026-11-16" for row in result["weekly"]))  # 周一
