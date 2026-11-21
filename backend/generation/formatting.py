"""Serialization and display helpers shared by generation and tool events."""


def snapshot_messages(messages):
    rows = []
    for message in messages:
        row = {
            "type": getattr(message, "type", type(message).__name__),
            "content": message.content,
        }
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            row["tool_calls"] = tool_calls
        tool_call_id = getattr(message, "tool_call_id", None)
        if tool_call_id:
            row["tool_call_id"] = tool_call_id
        name = getattr(message, "name", None)
        if name:
            row["name"] = name
        rows.append(row)
    return rows


def describe_location(location):
    if not location:
        return ""
    path = location.get("path", "")
    if location.get("page"):
        return f"{path} · 第 {location['page']} 页"
    if location.get("start_line") is not None:
        return f"{path}:{location['start_line']}–{location.get('end_line')}"
    return path


def top_results(results, limit=4):
    rows = []
    for item in results[:limit]:
        scores = item.get("scores") or {}
        score = next(
            (
                scores[name]
                for name in ("cross_encoder", "rrf", "cosine_similarity", "bm25")
                if name in scores
            ),
            None,
        )
        rows.append(
            {
                "id": item.get("id"),
                "label": describe_location(item.get("location") or {}),
                "score": score,
            }
        )
    return rows
