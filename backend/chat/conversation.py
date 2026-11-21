"""Deterministic follow-up context; no additional model call or query agent."""

import re


def retrieval_query(question, history):
    if len(question) > 160 or not re.search(
        r"它|这个|那个|上述|刚才|那为什么|那如何|\b(it|its|that|this|they|their)\b",
        question,
        re.I,
    ):
        return question
    previous = [message.content for message in history if message.role == "user"][-3:]
    return (
        "\n".join([text[:1000] for text in previous] + [question])
        if previous
        else question
    )
