from __future__ import annotations
import heapq
from .models import Event, World
from . import config


class EventEngine:
    def __init__(self, world: World) -> None:
        self.world = world
        self._handlers: dict[str, callable] = {}

    def register(self, event_type: str, handler: callable) -> None:
        self._handlers[event_type] = handler

    def schedule(self, event: Event) -> None:
        heapq.heappush(self.world.event_queue, event)

    def run(self) -> None:
        w = self.world
        while w.event_queue and w.clock < config.MAX_VIRTUAL_TIME:
            event = heapq.heappop(w.event_queue)
            w.clock = event.trigger_time
            w.event_count += 1
            self.dispatch(event)
            if w.event_count % config.METRICS_INTERVAL == 0:
                self._record_metrics()

    def dispatch(self, event: Event) -> None:
        handler = self._handlers.get(event.type)
        if handler:
            handler(self.world, event)

    def _record_metrics(self) -> None:
        from .metrics import snapshot
        self.world.metrics_log.append(snapshot(self.world))
