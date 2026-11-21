"""OpenAI-compatible client configuration and streaming callbacks."""

from ..core.config import settings
from .events import reasoning_state, token_sink


def model():
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_openai import ChatOpenAI

    sink = token_sink.get()
    state = reasoning_state.get()
    options = {}
    if settings.llm_reasoning_effort:
        options["reasoning_effort"] = settings.llm_reasoning_effort
    if settings.llm_max_tokens:
        options["max_tokens"] = settings.llm_max_tokens

    class CompatibleChatOpenAI(ChatOpenAI):
        """Keep provider reasoning fields that ChatOpenAI otherwise discards."""

        def _convert_chunk_to_generation_chunk(
            self, chunk, default_chunk_class, base_generation_info
        ):
            generation = super()._convert_chunk_to_generation_chunk(
                chunk, default_chunk_class, base_generation_info
            )
            try:
                choices = chunk.get("choices") or chunk.get("chunk", {}).get(
                    "choices", []
                )
                delta = choices[0].get("delta") if choices else None
                reasoning = delta.get("reasoning_content") if delta else None
                if generation is not None and isinstance(reasoning, str) and reasoning:
                    message = generation.message
                    message.additional_kwargs["reasoning_content"] = (
                        message.additional_kwargs.get("reasoning_content", "")
                        + reasoning
                    )
            except (AttributeError, IndexError, KeyError, TypeError):
                pass
            return generation

        def _create_chat_result(self, response, generation_info=None):
            result = super()._create_chat_result(response, generation_info)
            try:
                raw = (
                    response
                    if isinstance(response, dict)
                    else response.model_dump(exclude_none=True)
                )
                message = raw["choices"][0]["message"]
                reasoning = message.get("reasoning_content")
                if reasoning and result.generations:
                    result.generations[0].message.additional_kwargs[
                        "reasoning_content"
                    ] = reasoning
            except (AttributeError, IndexError, KeyError, TypeError):
                pass
            return result

    class TokenCallback(BaseCallbackHandler):
        def on_llm_new_token(self, token, *, chunk=None, **kwargs):
            if state is not None and chunk is not None:
                message = getattr(chunk, "message", None)
                extra = getattr(message, "additional_kwargs", None) or {}
                reasoning = extra.get("reasoning_content")
                if isinstance(reasoning, str) and reasoning:
                    state.add(reasoning)
            if sink and isinstance(token, str) and token:
                sink(token)

    return CompatibleChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or None,
        temperature=0,
        timeout=120,
        max_retries=1,
        streaming=True,
        callbacks=[TokenCallback()] if (sink or state is not None) else [],
        **options,
    )
