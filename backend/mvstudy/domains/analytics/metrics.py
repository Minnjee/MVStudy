"""学情统计口径：从业务快照计算可复算的指标。

本模块只做纯计算，不访问数据库、不依赖其他域，方便用工单 08 的固定数据
单独验证。时区按 Asia/Shanghai，统计区间为左闭右开 [from, to)。
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

# 上海时间固定偏移 +08:00，无需额外依赖
SHANGHAI = timezone(timedelta(hours=8))

# 成绩分档，顺序与展示一致
SCORE_BANDS = ((60, "<60"), (80, "60–<80"), (90, "80–<90"), (101, "90–100"))


def _parse(value: str | datetime) -> datetime:
    """把 ISO 8601 字符串或 datetime 统一成带时区的 datetime。"""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=SHANGHAI)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _in_range(moment: str | datetime, start: str | datetime, end: str | datetime) -> bool:
    moment = _parse(moment)
    low, high = _parse(start), _parse(end)
    return low <= moment < high


def _week_key(moment: str | datetime) -> str:
    """按周一分周，返回该周周一的日期字符串（上海时区）。"""
    local = _parse(moment).astimezone(SHANGHAI)
    monday = local.date() - timedelta(days=local.weekday())
    return monday.isoformat()


def _ratio(numerator: int, denominator: int) -> float | None:
    """没有分母返回 None（页面显示"暂无数据"），否则返回比例。"""
    return None if denominator == 0 else numerator / denominator


def completion_rate(
    assignment_recipients: Iterable[dict[str, Any]],
    submissions: Iterable[dict[str, Any]],
    *,
    start: str | datetime,
    end: str | datetime,
    as_of: str | datetime,
) -> dict[str, int | float | None]:
    """完成率 = 已提交的学生-任务对 / 应交的学生-任务对。

    - 分母：区间内发布的任务，其发布时的应交名单快照（assignment_recipients）。
    - 分子：同一(学生,任务)只算一次；取 min(to, as_of) 之前的提交。
    - 一人重交、一人交多次都只计一个学生-任务对。
    """
    cutoff = min(_parse(end), _parse(as_of))
    recipients = {
        (r["student_id"], r["assignment_id"])
        for r in assignment_recipients
        if _in_range(r["published_at"], start, end)
    }
    submitted = {
        (s["student_id"], s["assignment_id"])
        for s in submissions
        if _parse(s["submitted_at"]) <= cutoff
    }
    submitted_pairs = len(recipients & submitted)
    assigned_pairs = len(recipients)
    return {
        "submitted_pairs": submitted_pairs,
        "assigned_pairs": assigned_pairs,
        "completion_rate": _ratio(submitted_pairs, assigned_pairs),
    }


def run_success_rate(runs: Iterable[dict[str, Any]]) -> float | None:
    """运行成功率 = 成功数 / 已终态运行数（queued/running 不计入分母）。"""
    ended = [r for r in runs if r["status"] in ("succeeded", "failed")]
    return _ratio(sum(r["status"] == "succeeded" for r in ended), len(ended))


def top_topics(events: Iterable[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    """高频知识点：只数 5 号的 question.answered 事件。

    - topic 为空归入"未分类"。
    - 次数相同的按标签名排序，保证结果稳定可复算。
    """
    counts = Counter(
        (e.get("topic") or "未分类")
        for e in events
        if e["type"] == "question.answered"
    )
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"topic": topic, "count": count} for topic, count in ordered[:limit]]


def weekly_trend(
    assignment_recipients: Iterable[dict[str, Any]],
    submissions: Iterable[dict[str, Any]],
    *,
    start: str | datetime,
    end: str | datetime,
) -> list[dict[str, Any]]:
    """按周一分周的完成趋势，每周给出该周应交/已交的累加快照。"""
    recipients = list(assignment_recipients)
    submits = list(submissions)
    buckets: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for r in recipients:
        if _in_range(r["published_at"], start, end):
            buckets[_week_key(r["published_at"])].add((r["student_id"], r["assignment_id"]))
    submitted_pairs = {(s["student_id"], s["assignment_id"]) for s in submits}
    result = []
    running_assigned: set[tuple[str, str]] = set()
    running_submitted: set[tuple[str, str]] = set()
    for week in sorted(buckets):
        running_assigned |= buckets[week]
        running_submitted |= buckets[week] & submitted_pairs
        result.append({
            "week": week,
            "submitted_pairs": len(running_submitted),
            "assigned_pairs": len(running_assigned),
        })
    return result


def score_distribution(
    submissions: Iterable[dict[str, Any]],
    grades: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """成绩分档：只看所选任务最新提交的已批成绩。"""
    grade_by_submission = {g["submission_id"]: g["score"] for g in grades}
    latest: dict[tuple[str, str], tuple[int, str]] = {}
    for s in submissions:
        key = (s["student_id"], s["assignment_id"])
        if key not in latest or s["revision"] > latest[key][0]:
            latest[key] = (s["revision"], s["submission_id"])
    counts = Counter()
    for _key, (_revision, submission_id) in latest.items():
        score = grade_by_submission.get(submission_id)
        if score is None:  # 未批不计入分布
            continue
        for threshold, label in SCORE_BANDS:
            if score < threshold:
                counts[label] += 1
                break
    return [{"band": label, "count": counts[label]} for _t, label in SCORE_BANDS]


def build_analytics(
    *,
    class_id: str,
    recipients: Iterable[dict[str, Any]],
    submissions: Iterable[dict[str, Any]],
    runs: Iterable[dict[str, Any]],
    events: Iterable[dict[str, Any]],
    grades: Iterable[dict[str, Any]],
    start: str | datetime,
    end: str | datetime,
    as_of: str | datetime,
) -> dict[str, Any]:
    """汇总 E2 响应：一次快照算齐所有指标，周报复用同一结果。"""
    recipients = list(recipients)
    submissions = list(submissions)
    completion = completion_rate(recipients, submissions, start=start, end=end, as_of=as_of)
    return {
        "class_id": class_id,
        "as_of": _parse(as_of).isoformat(),
        **completion,
        "run_success_rate": run_success_rate(runs),
        "top_topics": top_topics(events),
        "weekly": weekly_trend(recipients, submissions, start=start, end=end),
        "scores": score_distribution(submissions, grades),
    }


def build_weekly_report(metrics: dict[str, Any]) -> dict[str, Any]:
    """E3 周报：摘要与建议基于同一统计快照，数字可倒推。"""
    assigned = metrics["assigned_pairs"]
    submitted = metrics["submitted_pairs"]
    if assigned == 0:
        summary = "本周暂无应交任务，暂无数据。"
    else:
        summary = f"{assigned} 个应交名额中已有 {submitted} 个提交。"
    suggestions: list[str] = []
    if metrics["completion_rate"] is not None and metrics["completion_rate"] < 0.8:
        suggestions.append("课堂提醒未提交的同学，并说明提交要求。")
    if metrics["top_topics"]:
        topic = metrics["top_topics"][0]["topic"]
        suggestions.append(f"针对高频知识点「{topic}」安排一次讲解。")
    if not suggestions:
        suggestions.append("本周各项指标正常，保持现有节奏。")
    return {
        "class_id": metrics["class_id"],
        "as_of": metrics["as_of"],
        "summary": summary,
        "suggestions": suggestions,
        "metrics": metrics,
    }
