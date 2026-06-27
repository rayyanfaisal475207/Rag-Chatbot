# ============================================================
# LLM Client — Groq (primary) + Gemini + OpenAI + Anthropic
#
# PROVIDER STRATEGY:
#   LLM_PROVIDER=groq   → LLaMA 3.3 70B via Groq (~200ms/call, free tier)
#   LLM_PROVIDER=gemini → Gemini 2.5 Flash via new google-genai SDK
#
# SDK NOTE: The old google-generativeai package is deprecated.
# We now use the new google-genai package (google.genai).
# ============================================================

import logging
from typing import AsyncGenerator

from src import config

logger = logging.getLogger(__name__)


async def call_llm(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.0,
    max_tokens: int = 1000,
    response_format: str = "text",
) -> str:
    """
    Non-streaming LLM call — returns the full response as a string.
    Used by: query_rewriter, router, evaluator.
    """
    if config.LLM_PROVIDER == "groq":
        return await _call_groq(system_prompt, user_message, temperature, max_tokens)
    elif config.LLM_PROVIDER == "gemini":
        return await _call_gemini(system_prompt, user_message, temperature, max_tokens)
    elif config.LLM_PROVIDER == "openai":
        return await _call_openai(system_prompt, user_message, temperature, max_tokens, response_format)
    elif config.LLM_PROVIDER == "anthropic":
        return await _call_anthropic(system_prompt, user_message, temperature, max_tokens)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {config.LLM_PROVIDER!r}")


async def stream_llm(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> AsyncGenerator[str, None]:
    """
    Streaming LLM call — yields tokens as they arrive.
    Used by: final response generator.
    """
    if config.LLM_PROVIDER == "groq":
        async for chunk in _stream_groq(system_prompt, user_message, temperature, max_tokens):
            yield chunk
    elif config.LLM_PROVIDER == "gemini":
        async for chunk in _stream_gemini(system_prompt, user_message, temperature, max_tokens):
            yield chunk
    elif config.LLM_PROVIDER == "openai":
        async for chunk in _stream_openai(system_prompt, user_message, temperature, max_tokens):
            yield chunk
    elif config.LLM_PROVIDER == "anthropic":
        async for chunk in _stream_anthropic(system_prompt, user_message, temperature, max_tokens):
            yield chunk
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {config.LLM_PROVIDER!r}")


# ── Groq ───────────────────────────────────────────────────────────────────────

async def _call_groq(system_prompt, user_message, temperature, max_tokens):
    import asyncio
    from groq import Groq

    client = Groq(api_key=config.GROQ_API_KEY)
    response = await asyncio.to_thread(
        lambda: client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    )
    return response.choices[0].message.content or ""


async def _stream_groq(system_prompt, user_message, temperature, max_tokens):
    import asyncio
    from groq import Groq

    client = Groq(api_key=config.GROQ_API_KEY)
    stream = await asyncio.to_thread(
        lambda: client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


# ── Gemini (new google-genai SDK) ──────────────────────────────────────────────

async def _call_gemini(system_prompt, user_message, temperature, max_tokens):
    """Non-streaming Gemini call using the new google-genai SDK."""
    import asyncio
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    response = await asyncio.to_thread(
        lambda: client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
    )
    return response.text or ""


async def _stream_gemini(system_prompt, user_message, temperature, max_tokens):
    """Streaming Gemini call using the new google-genai SDK."""
    import asyncio
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    # generate_content_stream runs synchronously, wrap in thread
    def _do_stream():
        return client.models.generate_content_stream(
            model=config.GEMINI_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )

    stream = await asyncio.to_thread(_do_stream)
    for chunk in stream:
        if chunk.text:
            yield chunk.text


# ── OpenAI (kept for compatibility) ───────────────────────────────────────────

async def _call_openai(system_prompt, user_message, temperature, max_tokens, response_format):
    import asyncio
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    kwargs = dict(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if response_format == "json":
        kwargs["response_format"] = {"type": "json_object"}
    response = await asyncio.to_thread(lambda: client.chat.completions.create(**kwargs))
    return response.choices[0].message.content or ""


async def _stream_openai(system_prompt, user_message, temperature, max_tokens):
    import asyncio
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    stream = await asyncio.to_thread(
        lambda: client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


# ── Anthropic (kept for compatibility) ────────────────────────────────────────

async def _call_anthropic(system_prompt, user_message, temperature, max_tokens):
    import asyncio
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = await asyncio.to_thread(
        lambda: client.messages.create(
            model=config.ANTHROPIC_MODEL,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    )
    return response.content[0].text if response.content else ""


async def _stream_anthropic(system_prompt, user_message, temperature, max_tokens):
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    with client.messages.stream(
        model=config.ANTHROPIC_MODEL,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
        temperature=temperature,
        max_tokens=max_tokens,
    ) as stream:
        for text_chunk in stream.text_stream:
            yield text_chunk
