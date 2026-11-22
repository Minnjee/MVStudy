"""Q1 服务：把检索结果包装成带出处的回答。"""
from .retrieval import search


def answer_question(question, materials, actor):
    """回答一个问题，返回 status / answer / citations。"""
    if not question or not question.strip():
        raise ValueError("empty_question")

    hits = search(question, materials, actor)
    if not hits:
        return {
            "status": "insufficient_evidence",
            "answer": "课程材料中未找到与该问题相关的依据。",
            "citations": [],
        }

    answer = "\n\n".join(chunk.content for _, chunk in hits)
    citations = [
        {"material_id": chunk.material_id, "locator": chunk.locator}
        for _, chunk in hits
    ]
    return {"status": "answered", "answer": answer, "citations": citations}