"""自制课程材料：供 05 号票本地测试用，不是真实课程材料。"""
from .models import Material
# 讲义：用 # 表示章，## 表示知识点（后面切分器会按这个认章节）
LECTURE = """# 第1章 图像阈值
## 1.1 双阈值原理
双阈值连接边缘：高阈值确定强边缘，低阈值连接弱边缘。
## 1.2 参数选择
低阈值通常取高阈值的一半。

# 第2章 高斯滤波
## 2.1 作用
高斯滤波用于降噪，先平滑再求梯度。
"""


# 代码材料
CODE = '''import cv2

def canny(image, low, high):
    """双阈值边缘检测。"""
    return cv2.Canny(image, low, high)
'''

# notebook：它的正文其实是 JSON 文本，注意引号别写错
NOTEBOOK = """{"cells": [
  {"cell_type": "markdown", "source": ["# 训练曲线"]},
  {"cell_type": "code", "source": ["plt.plot(loss)"]}
]}"""

# 习题
EXERCISE = """简述双阈值的连接作用。

说明高斯滤波的降噪原理。"""

# 答案：这是教师专用材料
ANSWER = """参考答案：高阈值确定强边缘，低阈值连接弱边缘。

参考答案：先平滑图像再求梯度可以降低噪声影响。"""

# 把 5 份材料装进一个列表
COURSE_MATERIALS = [
    Material(material_id="m-lecture", case_id="edge-case", version=1,
             kind="lecture", title="边缘检测讲义", visibility="course", content=LECTURE),
    Material(material_id="m-code", case_id="edge-case", version=1,
             kind="code", title="canny.py", visibility="course", content=CODE),
    Material(material_id="m-nb", case_id="edge-case", version=1,
             kind="notebook", title="实验.ipynb", visibility="course", content=NOTEBOOK),
    Material(material_id="m-exercise", case_id="edge-case", version=1,
             kind="exercise", title="习题", visibility="course", content=EXERCISE),
    Material(material_id="m-answer", case_id="edge-case", version=1,
             kind="answer", title="参考答案", visibility="staff", content=ANSWER),
]

# 模拟"谁在提问"，供后面判断权限用
STUDENT = {"user_id": "s1", "role_id": "student"}
TEACHER = {"user_id": "t1", "role_id": "teacher"}