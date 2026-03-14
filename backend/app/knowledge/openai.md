# OpenAI Billing & Cost Expert Knowledge Base

## Pricing Model

Token-based billing. Input and output tokens priced separately.

### Current Model Pricing (per 1M tokens)
| Model | Input | Output | Context |
|-------|-------|--------|---------|
| GPT-4o | $2.50 | $10.00 | 128K |
| GPT-4o-mini | $0.15 | $0.60 | 128K |
| o3 | $10.00 | $40.00 | 200K |
| o3-mini | $1.10 | $4.40 | 200K |
| o4-mini | $1.10 | $4.40 | 200K |
| GPT-4 Turbo | $10.00 | $30.00 | 128K |
| text-embedding-3-small | $0.02 | — | 8K |
| text-embedding-3-large | $0.13 | — | 8K |

### Cost Reduction Strategies
1. **Prompt caching** — Cached input tokens are 50% off
2. **Batch API** — 50% discount, 24-hour turnaround
3. **Model selection** — GPT-4o-mini is 17x cheaper than GPT-4o for input
4. **Shorter prompts** — System prompt optimization can cut 30-50% of input tokens
5. **Max tokens limit** — Set max_tokens to prevent runaway output

## Common Cost Problems

### 1. "Our API bill tripled this month"
- New feature launched without token budgets
- Retry loops on errors re-sending full context
- Long conversation history sent with every request
- Fix: Token budgets per endpoint, conversation truncation

### 2. "Embeddings cost more than expected"
- Re-embedding unchanged documents
- Fix: Cache embeddings, only re-embed on change

### 3. "We're using GPT-4o for everything"
- Many tasks work fine with GPT-4o-mini (classification, extraction, formatting)
- Fix: Model routing — use mini for simple tasks, full for complex

## Usage API
- Endpoint: `/v1/organization/usage/{bucket_type}`
- Bucket types: completions, embeddings, images, audio, moderations
- Granularity: 1m, 1h, 1d
- Group by: model, project, api_key
- Also: `/v1/organization/costs` for dollar amounts
