# FIXTURE FILE — intentionally bad LLM usage for Cortex eval tests.
# DO NOT deploy or import this file in production code.

import anthropic

client = anthropic.Anthropic()


def call_model_no_error_handling(prompt: str) -> str:
    """No try/except, no max_tokens, no timeout — all three anti-patterns."""
    response = client.messages.create(
        model="claude-3-opus-20240229",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def call_with_hardcoded_model(prompt: str) -> str:
    """Hardcoded model name that should be pulled from config."""
    try:
        response = client.messages.create(
            model="gpt-4o",
            max_tokens=1024,
            timeout=30,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}") from e


def stream_without_timeout(messages: list) -> None:
    """Missing timeout on streaming call."""
    try:
        with client.messages.stream(
            model="claude-3-5-sonnet-20241022",
            max_tokens=512,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
    except anthropic.APIError as e:
        print(f"Error: {e}")
