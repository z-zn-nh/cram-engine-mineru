# LLM First Design

## Goal

Make normal TUI questions call an OpenAI-compatible LLM before MinerU/RAG is ready.

## Scope

This phase only replaces the placeholder free-text response in `CommandRouter`.
It does not parse PDFs, build vector search, or add local document retrieval.

## Data Flow

1. User types a natural-language question in `cram`.
2. `CommandRouter.handle()` records the user message.
3. Slash commands keep their current deterministic behavior.
4. Free-text questions build a small study-agent prompt and call `OpenAICompatibleClient`.
5. The answer is recorded in session memory and shown in the TUI.

## Configuration

The first version reads environment variables:

- `CRAM_LLM_API_KEY`: API key.
- `CRAM_LLM_BASE_URL`: OpenAI-compatible base URL. Defaults to `https://api.openai.com/v1`.
- `CRAM_LLM_MODEL`: model name. Defaults to `gpt-4o-mini`.

Secrets are never written to repo files or `.cram/`.

## Error Handling

If the API key is missing, the agent returns a clear setup message instead of crashing.
If the HTTP request fails or the provider response shape is unexpected, the agent returns a short failure message and keeps the TUI session alive.

## Future Work

The next phase can add local Markdown/TXT retrieval and later MinerU-produced chunks into the prompt.
That is the postponed C plan.
