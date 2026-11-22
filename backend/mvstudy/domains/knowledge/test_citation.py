"""05 号票验收测试：切分、权限、带出处回答、HTTP 接口。"""
import unittest

from flask import Flask

from mvstudy.domains.knowledge.chunking import chunk_material
from mvstudy.domains.knowledge.fixtures import COURSE_MATERIALS, STUDENT, TEACHER
from mvstudy.domains.knowledge.retrieval import visible_materials
from mvstudy.domains.knowledge.routes import knowledge_api
from mvstudy.domains.knowledge.service import answer_question


class CitationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.extensions["knowledge_materials"] = COURSE_MATERIALS
        cls.app.extensions["knowledge_actor"] = STUDENT
        cls.app.register_blueprint(knowledge_api)
        cls.client = cls.app.test_client()

    def test_lecture_chunks_by_chapter(self):
        lecture = next(m for m in COURSE_MATERIALS if m.material_id == "m-lecture")
        locators = [c.locator for c in chunk_material(lecture)]
        self.assertEqual(len(locators), 3)
        self.assertIn("1.1 双阈值原理", locators[0])

    def test_code_chunks_by_function(self):
        code = next(m for m in COURSE_MATERIALS if m.material_id == "m-code")
        self.assertEqual([c.locator for c in chunk_material(code)], ["canny"])

    def test_notebook_chunks_by_cell(self):
        nb = next(m for m in COURSE_MATERIALS if m.material_id == "m-nb")
        self.assertEqual(len(chunk_material(nb)), 2)

    def test_student_cannot_see_answer(self):
        ids = [m.material_id for m in visible_materials(COURSE_MATERIALS, STUDENT)]
        self.assertNotIn("m-answer", ids)

    def test_teacher_can_see_answer(self):
        ids = [m.material_id for m in visible_materials(COURSE_MATERIALS, TEACHER)]
        self.assertIn("m-answer", ids)

    def test_answer_has_citations(self):
        result = answer_question("高阈值的作用", COURSE_MATERIALS, STUDENT)
        self.assertEqual(result["status"], "answered")
        self.assertTrue(result["citations"])

    def test_insufficient_evidence(self):
        result = answer_question("今天天气如何xyz", COURSE_MATERIALS, STUDENT)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["citations"], [])

    def test_http_question_endpoint(self):
        response = self.client.post("/api/questions", json={"question": "高阈值的作用"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "answered")

    def test_http_empty_question(self):
        response = self.client.post("/api/questions", json={"question": ""})
        self.assertEqual(response.status_code, 400)


if __name__ == "__&#8203;main__":
    unittest.main()