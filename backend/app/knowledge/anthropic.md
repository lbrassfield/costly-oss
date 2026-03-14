# Anthropic Billing & Cost Expert Knowledge Base

## Pricing Model

Token-based billing. Input/output priced separately. Extended thinking tokens billed as output.

### Current Model Pricing (per 1M tokens)
| Model | Input | Output | Context |
|-------|-------|--------|---------|
| Claude Opus 4 | $15.00 | $75.00 | 200K |
| Claude Sonnet 4 | $3.00 | $15.00 | 200K |
| Claude Haiku 3.5 | $0.80 | $4.00 | 200K |

### Prompt Caching (Major Cost Saver)
- Cached input tokens: 90% discount (only 10% of regular input price)
- Cache write: 25% premium on first write
- Cache TTL: 5 minutes (extended on each cache hit)
- **Best for:** System prompts, long documents, few-shot examples
- Breakeven: If prompt is reused 2+ times within 5 minutes

### Batch API
- 50% discount on both input and output
- 24-hour processing window
- Best for: bulk classification, evaluation, data processing

## Cost Optimization Strategies

1. **Prompt caching** — Cache system prompts and reference docs (90% savings on cached portion)
2. **Model routing** — Haiku for classification/extraction ($0.80 vs $15.00 input)
3. **Batch API** — For non-real-time workloads (50% off)
4. **Extended thinking control** — Set budget_tokens to limit thinking costs
5. **Max tokens** — Always set to prevent runaway output

## Common Cost Problems

### 1. "Opus costs are out of control"
- Extended thinking can generate 10x more tokens than the visible output
- Each thinking token billed at output rate ($75/1M for Opus)
- Fix: Use budget_tokens parameter, route simple tasks to Haiku

### 2. "Not using prompt caching"
- Every request sends the full system prompt as new input
- Fix: Use cache_control breakpoints on static content

## Admin API for Usage
- Endpoint: `/v1/organizations/usage`
- Requires admin API key (from console.anthropic.com > Organization Settings)
- Granularity: daily
- Group by: model
- Regular API keys cannot access usage data
