from pathlib import Path

from backend.pdf_source import pdf_chunks


def test_textbook_chunks_have_real_pages_and_no_fake_lines():
    path = Path("data/book-riscv-rev3.pdf")
    if not path.exists():
        import pytest

        pytest.skip("Local source corpus is not distributed with repository")
    body, location = next(pdf_chunks(path))
    assert body.strip()
    assert location["page"] >= 1
    assert location["start_line"] is None and location["end_line"] is None
    assert location["line_basis"] == "pdf_page"
