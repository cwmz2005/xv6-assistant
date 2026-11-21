"""Citation validation and final-answer normalization."""

import re


def finalize_answer(answer, evidence, finish_reason):
    allowed = {item["id"] for item in evidence}

    def resolve(match):
        matches = [cid for cid in allowed if cid.startswith(match.group(1))]
        return "[" + matches[0] + "]" if len(matches) == 1 else "[无法核验的引用已移除]"

    answer = re.sub(r"\[([0-9a-f]{8,64})\]", resolve, answer)
    if finish_reason == "length":
        answer += "\n\n> 本次生成达到输出上限，回答尚未完成。"
    citations = [item for item in evidence if "[" + item["id"] + "]" in answer]
    return answer, citations
