import json
from app.config import settings
from app.services.snowflake import (
    sync_dashboard, sync_costs, sync_queries, sync_storage,
    sync_warehouses, sync_workloads, sync_recommendations,
    sync_warehouse_sizing, sync_autosuspend_analysis,
    sync_spillage, sync_query_patterns, sync_cost_attribution,
    sync_stale_tables, get_credit_price,
)
from app.services.demo import (
    generate_demo_dashboard, generate_demo_costs, generate_demo_queries,
    generate_demo_storage, generate_demo_warehouses, generate_demo_workloads,
    generate_demo_recommendations, generate_demo_warehouse_sizing,
    generate_demo_autosuspend, generate_demo_spillage,
    generate_demo_query_patterns, generate_demo_cost_attribution,
    generate_demo_stale_tables,
)

TOOLS = [
    {
        "name": "get_dashboard",
        "description": "Get cost dashboard summary: daily cost trends, top warehouses by spend, query metrics (total/expensive/failed), top users, storage snapshot, and anomaly detection. Use this for high-level spend overview questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (1-365)", "default": 30}
            },
        },
    },
    {
        "name": "get_costs",
        "description": "Get detailed cost breakdown: daily costs per warehouse (compute + cloud services) and top users by cost. Use this for questions about cost trends, per-warehouse spend, or per-user spend.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (1-365)", "default": 30}
            },
        },
    },
    {
        "name": "get_queries",
        "description": "Get query history: paginated list of queries sorted by duration. Includes execution time, bytes scanned, spillage, cache hit %, warehouse, user, and query text. Use for questions about slow queries, expensive queries, or query performance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (1-90)", "default": 7},
                "limit": {"type": "integer", "description": "Max queries to return", "default": 20},
            },
        },
    },
    {
        "name": "get_storage",
        "description": "Get storage analysis: top tables by size (active + time-travel + failsafe), storage trends, and per-database breakdown. Use for questions about storage costs, largest tables, or storage growth.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days for trend (1-365)", "default": 30}
            },
        },
    },
    {
        "name": "get_warehouses",
        "description": "Get warehouse details: current configs (size, state, auto_suspend, clusters), daily activity, load history (avg_running, avg_queued), and per-warehouse stats. Use for questions about warehouse utilization or configuration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (1-90)", "default": 30}
            },
        },
    },
    {
        "name": "get_workloads",
        "description": "Get workload patterns: queries grouped by parameterized hash showing execution count, total/avg/p95 duration, total credits, and sample query. Use for questions about recurring query patterns or workload analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (1-90)", "default": 30}
            },
        },
    },
    {
        "name": "get_recommendations",
        "description": "Get optimization recommendations: auto-suspend waste, repeated queries, full table scans, stale tables, slow queries. Each includes potential savings, effort, and priority. Use when asked about saving money or optimizing.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_warehouse_sizing",
        "description": "Get warehouse sizing recommendations: analyzes utilization and spillage to suggest upsizing or downsizing with estimated savings and DDL commands.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to analyze (1-90)", "default": 30}
            },
        },
    },
    {
        "name": "get_autosuspend_analysis",
        "description": "Get auto-suspend analysis: evaluates suspend/resume patterns and query inter-arrival times to recommend optimal auto-suspend settings with idle waste savings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to analyze (1-90)", "default": 30}
            },
        },
    },
    {
        "name": "get_spillage",
        "description": "Get spillage analysis: spillage by warehouse and user, plus top spilling queries. Spillage means queries writing temp data to disk (local or remote) — a sign of under-sized warehouses or inefficient queries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to analyze (1-90)", "default": 30}
            },
        },
    },
    {
        "name": "get_query_patterns",
        "description": "Get query pattern analysis: groups queries by pattern hash, shows cost, duration, scan ratio, spillage, cache hit rate. Flags patterns as cacheable, full_scan, or spilling with specific recommendations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to analyze (1-90)", "default": 30}
            },
        },
    },
    {
        "name": "get_cost_attribution",
        "description": "Get cost attribution: breaks down costs by user, by role, by database, and by warehouse. Also shows top 20 most expensive individual queries. Use for chargeback, blame, or understanding who/what is driving spend.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to analyze (1-90)", "default": 30}
            },
        },
    },
    {
        "name": "get_stale_tables",
        "description": "Get stale table analysis: tables not queried in 90+ days with estimated storage savings from dropping/archiving them. Calculates cost at $23/TB/month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to analyze (1-90)", "default": 30}
            },
        },
    },
    {
        "name": "get_platform_costs",
        "description": "Get unified cost summary across all connected data platforms (AWS, dbt Cloud, AI tokens, etc). Shows total cost, breakdown by platform, by category (compute/storage/transformation/ai_inference), by service, daily trends, and top resources. Use this for cross-platform cost questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (1-365)", "default": 30}
            },
        },
    },
    {
        "name": "get_connected_platforms",
        "description": "List all data platforms the user has connected (AWS, dbt Cloud, OpenAI, etc). Shows platform type, connection name, and last sync time. Use this to know what data sources are available.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_anomalies",
        "description": "Get detected cost anomalies: z-score spikes, day-over-day increases, week-over-week increases. Each anomaly includes severity (medium/high), affected platform/resource, cost vs baseline, and percentage change. Use this when asked about spikes, anomalies, unusual costs, or 'what happened'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back", "default": 30},
            },
        },
    },
]

BASE_SYSTEM_PROMPT = """You are Costly AI, an expert data platform cost analyst. You help users understand and optimize their data platform spending across all connected platforms — Snowflake, AWS services, dbt Cloud, AI APIs, and more.

You have access to tools that query cost and usage data across the user's connected platforms. Use them to answer questions with specific numbers and actionable recommendations.

When answering cross-platform questions, use get_platform_costs to see the unified view. For Snowflake-specific deep dives, use the specialized Snowflake tools (get_dashboard, get_costs, etc).

Guidelines:
- Always ground your answers in actual data — call the relevant tools before answering
- When discussing costs, use dollar amounts and percentages
- When suggesting optimizations, include estimated savings
- Be concise and direct — lead with the key finding, then explain
- If multiple tools are needed to answer a question, call them in sequence
- When you don't have enough data to answer confidently, say so
- Format currency with $ and 2 decimal places
- Format large numbers with commas
- Use tables for comparisons when helpful"""


def _build_system_prompt(messages: list[dict]) -> str:
    """Build system prompt, routing to platform expert when relevant."""
    from app.services.expert_agents import get_expert_for_message, get_expert_system_prompt

    platform = get_expert_for_message(messages)
    if platform:
        expert_prompt = get_expert_system_prompt(platform)
        return f"{BASE_SYSTEM_PROMPT}\n\n{expert_prompt}"
    return BASE_SYSTEM_PROMPT


def _truncate(data, max_items: int = 30):
    """Truncate large lists in API responses to keep token usage reasonable."""
    if isinstance(data, list):
        if len(data) > max_items:
            return {"items": data[:max_items], "_note": f"Showing {max_items} of {len(data)} items"}
        return {"items": data}
    if not isinstance(data, dict):
        return data
    result = {}
    for k, v in data.items():
        if isinstance(v, list) and len(v) > max_items:
            result[k] = v[:max_items]
            result[f"_{k}_note"] = f"Showing {max_items} of {len(v)} items"
        else:
            result[k] = v
    return result


async def _call_tool(tool_name: str, tool_input: dict, source, credit_price: float, user_id: str = None) -> dict:
    """Execute a tool call against real Snowflake data or demo data."""
    from app.utils.helpers import run_in_thread

    # Handle cross-platform tools
    if tool_name == "get_platform_costs":
        if user_id and source is not None:
            from app.services.unified_costs import get_unified_costs
            return await get_unified_costs(user_id, tool_input.get("days", 30))
        else:
            from app.services.demo_platforms import generate_demo_unified_costs
            return generate_demo_unified_costs(tool_input.get("days", 30))
    if tool_name == "get_anomalies":
        if user_id:
            from app.services.anomaly_detector import get_anomalies
            return await get_anomalies(user_id, days=tool_input.get("days", 30))
        return {"anomalies": [], "message": "No anomaly data in demo mode"}
    if tool_name == "get_connected_platforms":
        if user_id and source is not None:
            from app.services.unified_costs import get_platform_connections
            conns = await get_platform_connections(user_id)
            return {"connections": [
                {"platform": c["platform"], "name": c["name"], "last_synced": c.get("last_synced")}
                for c in conns
            ]}
        else:
            from app.services.demo_platforms import generate_demo_platform_connections
            return {"connections": generate_demo_platform_connections()}

    is_demo = source is None
    days = tool_input.get("days", 30)

    tool_map_real = {
        "get_dashboard": lambda: run_in_thread(sync_dashboard, source, days, credit_price),
        "get_costs": lambda: run_in_thread(sync_costs, source, days, credit_price),
        "get_queries": lambda: run_in_thread(sync_queries, source, days, tool_input.get("limit", 20)),
        "get_storage": lambda: run_in_thread(sync_storage, source, days),
        "get_warehouses": lambda: run_in_thread(sync_warehouses, source, days, credit_price),
        "get_workloads": lambda: run_in_thread(sync_workloads, source, days, credit_price),
        "get_recommendations": lambda: run_in_thread(sync_recommendations, source, credit_price),
        "get_warehouse_sizing": lambda: run_in_thread(sync_warehouse_sizing, source, days, credit_price),
        "get_autosuspend_analysis": lambda: run_in_thread(sync_autosuspend_analysis, source, days, credit_price),
        "get_spillage": lambda: run_in_thread(sync_spillage, source, days),
        "get_query_patterns": lambda: run_in_thread(sync_query_patterns, source, days, credit_price),
        "get_cost_attribution": lambda: run_in_thread(sync_cost_attribution, source, days, credit_price),
        "get_stale_tables": lambda: run_in_thread(sync_stale_tables, source, days),
    }

    tool_map_demo = {
        "get_dashboard": lambda: generate_demo_dashboard(days),
        "get_costs": lambda: generate_demo_costs(days),
        "get_queries": lambda: generate_demo_queries(),
        "get_storage": lambda: generate_demo_storage(),
        "get_warehouses": lambda: generate_demo_warehouses(),
        "get_workloads": lambda: generate_demo_workloads(),
        "get_recommendations": lambda: generate_demo_recommendations(),
        "get_warehouse_sizing": lambda: generate_demo_warehouse_sizing(),
        "get_autosuspend_analysis": lambda: generate_demo_autosuspend(),
        "get_spillage": lambda: generate_demo_spillage(),
        "get_query_patterns": lambda: generate_demo_query_patterns(),
        "get_cost_attribution": lambda: generate_demo_cost_attribution(),
        "get_stale_tables": lambda: generate_demo_stale_tables(),
    }

    tool_map = tool_map_demo if is_demo else tool_map_real

    if tool_name not in tool_map:
        return {"error": f"Unknown tool: {tool_name}"}

    result = tool_map[tool_name]()
    if not is_demo:
        result = await result
    return _truncate(result)


def _get_llm_client():
    """Get the LLM client based on configured provider."""
    provider = settings.llm_provider
    if provider == "openai":
        from openai import OpenAI
        return "openai", OpenAI(api_key=settings.llm_api_key)
    else:
        import anthropic
        return "anthropic", anthropic.Anthropic(api_key=settings.llm_api_key)


async def run_agent(messages: list[dict], source, credit_price: float, user_id: str = None) -> str:
    """Run the Costly AI agent with tool use in a loop until a final text response."""
    provider, client = _get_llm_client()

    api_messages = []
    for msg in messages:
        api_messages.append({"role": msg["role"], "content": msg["content"]})

    system_prompt = _build_system_prompt(messages)

    while True:
        response = client.messages.create(
            model=settings.llm_model,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=api_messages,
        )

        if response.stop_reason == "end_turn":
            text_parts = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_parts)

        # Process tool uses
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = await _call_tool(block.name, block.input, source, credit_price, user_id)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })

        if not tool_results:
            text_parts = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_parts) if text_parts else "I wasn't able to process that request."

        # Append assistant response and tool results, then loop
        api_messages.append({"role": "assistant", "content": response.content})
        api_messages.append({"role": "user", "content": tool_results})
