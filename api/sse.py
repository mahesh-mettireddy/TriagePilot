"""
api/sse.py
----------
Server-Sent Events (SSE) streaming helpers.
Transforms asyncio event queues into sse-starlette EventSourceResponse streams.
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Optional
from sse_starlette.sse import ServerSentEvent

from engine.schemas import SSEEvent


async def event_generator(
    queue: asyncio.Queue[Optional[SSEEvent]],
) -> AsyncGenerator[ServerSentEvent, None]:
    """
    Consumes SSEEvent objects from the queue and yields ServerSentEvent instances.
    Exits cleanly when None is encountered.
    """
    while True:
        try:
            event = await queue.get()
            if event is None:
                # End of stream
                break
            yield ServerSentEvent(
                data=event.model_dump_json(),
                event=event.type,
                id=str(event.seq),
            )
        except asyncio.CancelledError:
            break
