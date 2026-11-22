"""Q1 的 HTTP 面：POST /api/questions。"""
from flask import Blueprint, current_app, jsonify, request

from .service import answer_question

knowledge_api = Blueprint("knowledge", __name__, url_prefix="/api")


@knowledge_api.post("/questions")
def post_question():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": {"code": "invalid_json", "message": "请求内容必须是 JSON 对象。"}}), 400

    question = body.get("question")
    if not isinstance(question, str) or not question.strip():
        return jsonify({"error": {"code": "empty_question", "message": "question 不能为空。"}}), 400

    materials = current_app.extensions.get("knowledge_materials", [])
    actor = current_app.extensions.get("knowledge_actor", {"role_id": "student"})

    result = answer_question(question, materials, actor)
    return jsonify(result)