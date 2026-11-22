"""05 号票用的数据结构：一份课程材料的"信息卡"。"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Material:
    material_id: str    # 材料唯一编号，例如 "m-lecture"
    case_id: str        # 属于哪个案例，例如 "edge-case"
    version: int        # 案例版本号，例如 1
    kind: str           # 类型：lecture 讲义 / code 代码 / exercise 习题 / answer 答案
    title: str          # 给人看的标题
    visibility: str     # 可见范围：course 学生可见 / staff 仅教师可见
    content: str        # 材料正文
    
    
@dataclass(frozen=True)
class Chunk:
    """切出来的小片段，locator 记录它来自哪里。"""
    chunk_id: str       # 片段编号
    material_id: str    # 来自哪份材料
    case_id: str        # 案例编号（继承材料）
    version: int        # 版本（继承材料）
    kind: str           # 材料类型（继承材料）
    title: str          # 材料标题（继承材料）
    visibility: str     # 可见范围（继承材料）
    locator: str        # 位置：章节/函数/单元格
    content: str        # 片段正文