import asyncio


class BaseAsyncClient:
    """Base class for asynchronous clients interacting with synchronous libraries."""
    def __init__(self):
        pass

    async def _run_sync(self, func, *args, **kwargs):
        """
        Helper method to run synchronous calls in a thread pool.
        This prevents blocking the async event loop.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
