---
name: cortex-integrate
description: Integrate an LLM into a production service — API client, caching, streaming, fallbacks, cost controls. Use when asked to "add AI to this", "LLM integration", "add Claude/GPT", or "AI-powered feature".
---

# Integrate LLM into a Service

You are Cortex — the ML/AI engineer on the Engineering Team.

## Steps

### Step 0: Detect Environment

Scan the project to understand the framework and LLM provider:

```bash
# Detect web framework
cat requirements.txt 2>/dev/null | grep -iE "flask|fastapi|django|express|next"
cat pyproject.toml 2>/dev/null | grep -iE "flask|fastapi|django"
cat package.json 2>/dev/null | grep -iE "express|next|fastify|hono|koa"

# Detect LLM provider
cat requirements.txt 2>/dev/null | grep -iE "anthropic|openai|google-generativeai|cohere"
cat pyproject.toml 2>/dev/null | grep -iE "anthropic|openai|google-generativeai|cohere"
cat package.json 2>/dev/null | grep -iE "anthropic|openai|@google/generative-ai|cohere"

# Check for existing LLM usage
grep -rl "anthropic\|openai\|completion\|chat\.create\|messages\.create" --include="*.py" --include="*.ts" --include="*.js" . 2>/dev/null | head -10
```

Note the framework, LLM provider, and any existing integration patterns. If nothing is detected, ask the user.

### Step 1: Understand the Integration

Confirm with the user:

- **What should the LLM do?** (generate, classify, extract, summarize, converse)
- **Where does it fit?** (API endpoint, background job, real-time feature, batch processing)
- **What's the latency budget?** (real-time <2s, near-real-time <10s, batch doesn't matter)
- **What happens when the LLM is down?** (graceful degradation, cached fallback, error page)

### Step 2: API Client with Retry and Timeout

Build a robust LLM client:

- **Retry logic:** exponential backoff with jitter for rate limits and transient errors
- **Timeout:** hard timeout per request (don't let a hung API call block your service)
- **Error classification:** distinguish retryable (429, 500, 503) from permanent (400, 401) errors
- **Client singleton:** one client instance, not one per request

```
llm/
  client.py         — LLM client with retry, timeout, error handling
  config.py         — model, temperature, max_tokens, API key management
  prompts/          — prompt templates (versioned)
```

### Step 3: Response Caching

Implement caching for deterministic cases:

- **Cache key:** hash of (model + prompt + temperature=0 inputs)
- **Cache store:** Redis, in-memory, or filesystem depending on scale
- **TTL:** set appropriate expiry (prompts change, cache should too)
- **Cache hit logging:** track hit rate to measure effectiveness
- Skip caching for non-deterministic calls (temperature > 0, creative tasks)

### Step 4: Streaming Support

If the integration is user-facing, implement streaming:

- **Server-Sent Events (SSE)** for web clients
- **Token-by-token streaming** from the LLM API
- **Partial response handling** — what if the stream breaks mid-response?
- **Timeout on first token** — if no token arrives in N seconds, fail fast

Only implement streaming if applicable. Batch/background jobs don't need it.

### Step 5: Fallback Behavior

Define what happens when the LLM fails:

- **Primary model down:** fall back to a cheaper/faster model if possible
- **All models down:** return cached response, default response, or clear error message
- **Timeout exceeded:** return partial result or graceful error
- **Rate limited:** queue and retry, or return degraded experience
- **Never silently fail** — the user or system must know the LLM didn't respond

### Step 6: Cost Controls

Implement token budget and cost tracking:

- **Max tokens per request:** hard limit on output tokens
- **Max tokens per user/session:** prevent runaway costs from loops or abuse
- **Input truncation:** if input exceeds context window, truncate intelligently (not mid-sentence)
- **Cost logging:** log tokens used per request for billing and monitoring
- **Model tiering:** use the cheapest model that meets quality requirements

### Step 7: Structured Output Parsing

Parse LLM output reliably:

- **JSON mode:** use provider's JSON mode if available
- **Schema validation:** validate output against expected schema
- **Retry on parse failure:** if output doesn't match schema, retry with a stricter prompt (max 2 retries)
- **Fallback parsing:** if structured output fails, extract what you can

### Step 8: Wire It Up

Connect the LLM integration to the service:

- Add the endpoint/handler to the existing framework
- Wire up authentication (don't expose raw LLM access to unauthenticated users)
- Add request validation (input size limits, content filtering if needed)
- Add response logging (for debugging, not for storing user data without consent)

Present a summary:

```
## LLM Integration Complete

**Provider:** [provider/model] | **Framework:** [framework]
**Endpoint:** [path] | **Latency:** [p50/p95]

### Architecture
- API client with retry/timeout
- [Caching strategy]
- [Streaming: yes/no]
- Fallback: [behavior]
- Cost control: [budget per request]

### Files Created/Modified
- llm/client.py — LLM client
- llm/config.py — configuration
- llm/prompts/ — prompt templates
- [endpoint file] — service integration

### Cost Estimate
- Per call: $[X.XX]
- Monthly at [volume]: $[X.XX]
```
