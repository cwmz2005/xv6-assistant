"""Source-aware chunks with exact original line ranges."""

import re
from pathlib import Path


def split(text, path, max_lines=80):
    lines = text.splitlines()
    code = Path(path).suffix.lower() in {".c", ".h", ".s"}
    boundaries = [(0, "")]
    for i, line in enumerate(lines):
        symbol = ""
        if code:
            match = re.match(r"^([A-Za-z_]\w*)\s*\([^;]*$", line)
            struct = re.match(r"^(?:typedef\s+)?struct\s+(\w+)\s*\{", line)
            if match and i + 1 < len(lines) and lines[i + 1].strip() == "{":
                symbol = match[1]
            elif struct:
                symbol = struct[1]
        elif re.match(r"^#{1,6}\s+", line):
            symbol = line.lstrip("#").strip()
        if symbol:
            start = i
            if (
                code
                and i
                and re.match(r"^[\w\s*]+$", lines[i - 1])
                and lines[i - 1].strip()
            ):
                start = i - 1
            if start == boundaries[-1][0]:
                boundaries[-1] = (start, symbol)
            else:
                boundaries.append((start, symbol))
    for index, (start, symbol) in enumerate(boundaries):
        end = boundaries[index + 1][0] if index + 1 < len(boundaries) else len(lines)
        cursor = start
        while cursor < end:
            stop = min(cursor + max_lines, end)
            if stop < end:
                blanks = [
                    j
                    for j in range(cursor + max_lines // 2, stop)
                    if not lines[j].strip()
                ]
                if blanks:
                    stop = blanks[-1] + 1
            body = "\n".join(lines[cursor:stop])
            if body.strip():
                yield (
                    body,
                    {
                        "path": path,
                        "start_line": cursor + 1,
                        "end_line": stop,
                        "section": symbol,
                        "function": symbol if code else None,
                    },
                )
            cursor = stop
