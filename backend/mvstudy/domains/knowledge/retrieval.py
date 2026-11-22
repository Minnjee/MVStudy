"""检索：从可见材料里找出与问题相关的片段。"""
STAFF_ROLES = frozenset({"teacher", "admin"})


def visible_materials(materials, actor):
    """按提问人身份过滤：学生只能看 course，教师能看全部。"""
    if actor.get("role_id") in STAFF_ROLES:
        return list(materials)
    return [m for m in materials if m.visibility == "course"]

import re

_TOKEN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def _tokens(text):
    """把文本拆成一串小块：英文单词整体，中文单字。"""
    return _TOKEN.findall(text.lower())


def _ngrams(items):
    """造"特征"：单个小块 + 相邻两个小块的组合。"""
    grams = set(items)
    grams.update(a + b for a, b in zip(items, items[1:]))
    return grams


def _score(question, text):
    """算相关性得分：问题的特征里，有多少比例出现在材料里。"""
    q = _ngrams(_tokens(question))
    t = _ngrams(_tokens(text))
    if not q:
        return 0.0
    return len(q & t) / len(q)

from .chunking import chunk_material

MIN_SCORE = 0.3   # 命中线：低于此分视为"没依据"


def search(question, materials, actor, top_k=3):
    """在提问者可见的材料里，找出与问题最相关的若干片段。"""
    visible = visible_materials(materials, actor)
    candidates = []
    for material in visible:
        for chunk in chunk_material(material):
            score = _score(question, f"{chunk.title} {chunk.content}")
            if score >= MIN_SCORE:
                candidates.append((score, chunk))
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return candidates[:top_k]