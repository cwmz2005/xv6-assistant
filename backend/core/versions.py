"""Available source-code versions and branch labels."""

import json
from pathlib import Path

from sqlalchemy import select

from .database import Document

MANIFEST = Path(__file__).resolve().parents[2] / "evaluation/source-versions.json"


def version_labels():
    if not MANIFEST.exists():
        return {}
    return {
        row["commit"]: row["branch"]
        for row in json.loads(MANIFEST.read_text(encoding="utf-8"))
    }


def version_options(db):
    """Return imported code versions as model-selectable branch options."""
    labels = version_labels()
    commits = db.scalars(
        select(Document.version).distinct().where(~Document.version.like("directory-%"))
    )
    options = []
    seen = set()
    for commit in commits:
        label = labels.get(commit) or "自定义源码"
        value = label if label != "自定义源码" else commit
        if value in seen:
            continue
        seen.add(value)
        options.append({"value": value, "commit": commit, "label": label})
    return sorted(options, key=lambda option: option["label"])


def resolve_version(value, options):
    """Resolve a branch label or commit prefix to a concrete commit."""
    if value is None or not str(value).strip():
        return None, None, None
    value = str(value).strip()
    for option in options:
        if value in {option["value"], option["commit"]}:
            return option["commit"], option["label"], None
    matches = [option for option in options if option["commit"].startswith(value)]
    if len(matches) == 1:
        option = matches[0]
        return option["commit"], option["label"], None
    return None, None, "未知代码分支或提交"
