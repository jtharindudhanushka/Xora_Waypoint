"""GET /stream — Server-Sent Events filtered by the user's scope (docs/05 › SSE)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.deps import CurrentUser
from app.modules.stream.broker import broker

router = APIRouter(tags=["stream"])
HEARTBEAT_SECONDS = 15


@router.get("/stream", summary="Live updates (Server-Sent Events)")
async def stream(request: Request, user: CurrentUser) -> StreamingResponse:
    scope = {
        "user_id": str(user.id),
        "role": user.role,
        "depot": user.depot,
        "dock": user.dock,
        "vehicle": user.vehicle_code,
        "outlet": user.outlet_code,
    }

    async def events() -> AsyncIterator[str]:
        async with broker.subscribe(scope) as queue:
            yield "retry: 3000\n\n"
            while not await request.is_disconnected():
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                    yield message.encode()
                except TimeoutError:
                    yield ": heartbeat\n\n"  # keeps proxies from closing idle connections

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(events(), media_type="text/event-stream", headers=headers)
