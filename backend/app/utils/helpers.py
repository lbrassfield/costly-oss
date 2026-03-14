import asyncio
from datetime import datetime, timedelta
from functools import partial


def days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


async def run_in_thread(fn, *args):
    """Run a blocking function in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(fn, *args))
