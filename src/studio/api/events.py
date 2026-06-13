"""In-process SSE event bus for job progress.

Each episode has a list of subscriber queues; the background generator publishes
progress events (asset started/ready/failed, cost updates) and the SSE route
streams them to connected clients. Pure stdlib asyncio, no broker — fine for a
single-process studio backend.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List


class EventBus:
    """Fan-out of per-episode events to any number of async subscribers."""

    def __init__(self) -> None:
        self._subscribers: Dict[int, List[asyncio.Queue]] = {}

    def subscribe(self, episode_id: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(episode_id, []).append(queue)
        return queue

    def unsubscribe(self, episode_id: int, queue: asyncio.Queue) -> None:
        subs = self._subscribers.get(episode_id)
        if not subs:
            return
        if queue in subs:
            subs.remove(queue)
        if not subs:
            self._subscribers.pop(episode_id, None)

    def publish(self, episode_id: int, event: Dict[str, Any]) -> None:
        """Push an event to all subscribers of an episode (non-blocking)."""
        for queue in list(self._subscribers.get(episode_id, [])):
            queue.put_nowait(event)

    @staticmethod
    def format_sse(event: Dict[str, Any]) -> str:
        """Serialize one event as an SSE `data:` frame."""
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


# Module-level singleton shared by the generator and the SSE route.
bus = EventBus()
