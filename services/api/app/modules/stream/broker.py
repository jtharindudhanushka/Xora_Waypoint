"""In-process publish/subscribe for Server-Sent Events.

One API instance is enough at Waypoint's scale (docs/03 › Scale). The broker is an interface:
to run several instances, back `publish` with Postgres LISTEN/NOTIFY without touching callers.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any

Audience = Callable[[dict[str, Any]], bool]  # given a subscriber's scope, should it receive this?


@dataclass(frozen=True)
class Message:
    event: str
    data: dict[str, Any]
    audience: Audience | None = None

    def encode(self) -> str:
        return f"event: {self.event}\ndata: {json.dumps(self.data, default=str)}\n\n"


@dataclass(eq=False)  # identity-hashed: each connection is its own subscriber
class _Subscriber:
    scope: dict[str, Any]
    queue: asyncio.Queue[Message] = field(default_factory=lambda: asyncio.Queue(maxsize=100))


class Broker:
    def __init__(self) -> None:
        self._subscribers: set[_Subscriber] = set()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    async def publish(
        self, event: str, data: dict[str, Any], audience: Audience | None = None
    ) -> None:
        message = Message(event, data, audience)
        for sub in list(self._subscribers):
            if audience is None or audience(sub.scope):
                with contextlib.suppress(asyncio.QueueFull):  # slow client: drop, it will refetch
                    sub.queue.put_nowait(message)

    @contextlib.asynccontextmanager
    async def subscribe(self, scope: dict[str, Any]) -> AsyncIterator[asyncio.Queue[Message]]:
        sub = _Subscriber(scope)
        self._subscribers.add(sub)
        try:
            yield sub.queue
        finally:
            self._subscribers.discard(sub)


broker = Broker()
