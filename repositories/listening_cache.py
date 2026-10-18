"""Process-wide cache for listening aggregates that scan every scrobble.

The backend clears it whenever it writes scrobbles; the TTL bounds staleness from
writers outside this process (sync scripts, the Textual app, hand-run SQL).
"""
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Hashable


class ListeningCache:
    def __init__(self, ttl: float = 300, capacity: int = 64,
                 clock: Callable[[], float] = time.monotonic):
        self.ttl = ttl
        self.capacity = capacity
        self._clock = clock
        self._generation = 0
        self._entries: OrderedDict[Hashable, tuple[float, object]] = OrderedDict()

    async def get(self, key: Hashable, load: Callable[[], Awaitable]):
        entry = self._entries.get(key)
        if entry is not None and entry[0] > self._clock():
            self._entries.move_to_end(key)
            return entry[1]
        generation = self._generation
        value = await load()
        # A write during the load may have made this value stale already.
        if generation == self._generation:
            self._entries[key] = (self._clock() + self.ttl, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.capacity:
                self._entries.popitem(last=False)
        return value

    @property
    def revision(self) -> int:
        """Advances after every scrobble write, once it has been committed."""
        return self._generation

    def invalidate(self) -> None:
        self._generation += 1
        self._entries.clear()


listening_cache = ListeningCache()
