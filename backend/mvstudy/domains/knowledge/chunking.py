"""按材料类型切分，产出可定位的片段。"""
from __future__ import annotations

import ast      #能读懂代码结构，认出这个def是函数，那个class是类
import json

from .models import Chunk, Material


def _make(material: Material, index: int, locator: str, content: str) -> Chunk:
    """把材料信息 + 位置 + 正文打包成一个 Chunk。"""
    return Chunk(
        chunk_id=f"{material.material_id}:{index}",
        material_id=material.material_id,
        case_id=material.case_id,
        version=material.version,
        kind=material.kind,
        title=material.title,
        visibility=material.visibility,
        locator=locator,
        content=content.strip(),
    )


def _chunk_lecture(material: Material) -> list[Chunk]:
    """讲义：认 # 作章、## 作知识点，遇到空行就切出一段。"""
    chunks: list[Chunk] = []
    chapter = topic = ""
    paragraph = 0
    buffer: list[str] = []

    def flush() -> None:
        nonlocal paragraph
        text = "\n".join(buffer).strip()
        buffer.clear()
        if not text:
            return
        paragraph += 1
        parts = [p for p in (chapter, topic, f"第{paragraph}段") if p]
        chunks.append(_make(material, len(chunks), "/".join(parts), text))

    for raw in material.content.splitlines():
        line = raw.strip()
        if line.startswith("# "):
            flush()
            chapter = line[2:].strip()
            topic = ""
            paragraph = 0
        elif line.startswith("## "):
            flush()
            topic = line[3:].strip()
            paragraph = 0
        elif not line:
            flush()
        else:
            buffer.append(line)
    flush()
    return chunks


def _chunk_code(material: Material) -> list[Chunk]:
    """代码：用 ast 认出函数和类，各自切成一段。"""
    try:
        tree = ast.parse(material.content)
    except SyntaxError:
        return [_make(material, 0, "整个文件", material.content)] if material.content.strip() else []
    lines = material.content.splitlines()
    chunks: list[Chunk] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            text = "\n".join(lines[node.lineno - 1: node.end_lineno])
            chunks.append(_make(material, len(chunks), node.name, text))
        elif isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    text = "\n".join(lines[member.lineno - 1: member.end_lineno])
                    chunks.append(_make(material, len(chunks), f"{node.name}.{member.name}", text))
    if not chunks and material.content.strip():
        chunks.append(_make(material, 0, "整个文件", material.content))
    return chunks


def _chunk_notebook(material: Material) -> list[Chunk]:
    """notebook：按 cells 顺序切，每段标上单元格序号。"""
    try:
        data = json.loads(material.content)
    except (ValueError, TypeError):
        return [_make(material, 0, "单元格[0]", material.content)] if material.content.strip() else []
    cells = data.get("cells", []) if isinstance(data, dict) else []
    chunks: list[Chunk] = []
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            continue
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(str(part) for part in source)
        text = str(source).strip()
        if not text:
            continue
        cell_type = cell.get("cell_type", "cell")
        chunks.append(_make(material, len(chunks), f"单元格[{index}] {cell_type}", text))
    return chunks


def _chunk_paragraphs(material: Material) -> list[Chunk]:
    """习题、答案等：按空行切成段。"""
    chunks: list[Chunk] = []
    for paragraph, raw in enumerate(material.content.split("\n\n"), start=1):
        text = raw.strip()
        if text:
            chunks.append(_make(material, len(chunks), f"第{paragraph}段", text))
    return chunks


def chunk_material(material: Material) -> list[Chunk]:
    """按材料类型分派到对应的切分器。"""
    if material.kind == "lecture":
        return _chunk_lecture(material)
    if material.kind == "code":
        return _chunk_code(material)
    if material.kind == "notebook":
        return _chunk_notebook(material)
    return _chunk_paragraphs(material)