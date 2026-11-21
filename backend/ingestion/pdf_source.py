"""Page-aware PDF extraction; PDF coordinates never masquerade as source lines."""

import re

from pypdf import PdfReader


def pdf_chunks(path, max_words=180):
    reader = PdfReader(path)
    labels = reader.page_labels
    sections = []

    def visit(outline):
        for item in outline:
            if isinstance(item, list):
                visit(item)
            else:
                try:
                    sections.append(
                        (reader.get_destination_page_number(item) + 1, str(item.title))
                    )
                except (ValueError, AttributeError, KeyError):
                    pass

    visit(reader.outline)
    sections.sort()
    for page_number, page in enumerate(reader.pages, 1):
        content = (
            page.extract_text(extraction_mode="layout", layout_mode_strip_rotated=False)
            or ""
        ).replace("\x00", "")
        section = next(
            (title for number, title in reversed(sections) if number <= page_number), ""
        )
        lines = content.splitlines()
        for line in lines[:12]:
            if re.match(r"^\s*(?:Chapter\s+\d+|\d+\.\d+(?:\.\d+)?\s+[A-Z])", line):
                section = line.strip()
                break
        paragraphs = re.split(r"\n\s*\n", content)
        pending = []
        size = 0
        part = 0
        for paragraph in paragraphs:
            words = paragraph.split()
            for offset in range(0, len(words), max_words):
                piece = words[offset : offset + max_words]
                if not any(re.search("[A-Za-z\u4e00-\u9fff]", w) for w in piece):
                    continue
                if pending and size + len(piece) > max_words:
                    part += 1
                    yield (
                        "\n\n".join(pending),
                        {
                            "page": page_number,
                            "page_label": labels[page_number - 1],
                            "section": section,
                            "part": part,
                            "line_basis": "pdf_page",
                            "start_line": None,
                            "end_line": None,
                        },
                    )
                    pending = []
                    size = 0
                pending.append(" ".join(piece))
                size += len(piece)
        if pending:
            yield (
                "\n\n".join(pending),
                {
                    "page": page_number,
                    "page_label": labels[page_number - 1],
                    "section": section,
                    "part": part + 1,
                    "line_basis": "pdf_page",
                    "start_line": None,
                    "end_line": None,
                },
            )


def pdf_report(path):
    reader = PdfReader(path)
    lengths = [len((p.extract_text() or "").strip()) for p in reader.pages]
    return {
        "pages": len(lengths),
        "text_characters": sum(lengths),
        "empty_pages": [i + 1 for i, n in enumerate(lengths) if n == 0],
        "short_pages": [i + 1 for i, n in enumerate(lengths) if 0 < n < 100],
    }
