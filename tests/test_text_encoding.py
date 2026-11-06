from pathlib import Path


def test_project_text_is_utf8_without_corruption():
    paths = [Path("README.md"), Path("frontend/index.html")]
    for root in ["backend", "frontend/src", "tests", "evaluation"]:
        paths.extend(
            p
            for p in Path(root).rglob("*")
            if p.suffix in {".py", ".tsx", ".ts", ".jsonl"}
        )
    replacement = chr(0xFFFD)
    repeated_question_marks = "?" * 3
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert replacement not in text, path
        assert repeated_question_marks not in text, path
    assert "知识" in Path("README.md").read_text(encoding="utf-8")
