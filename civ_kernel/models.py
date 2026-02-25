from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Agent:
    id: int
    wealth: float = 0.0
    energy: float = 0.0
    max_energy: float = 1.0
    regen_rate: float = 0.1
    neighbors: dict[int, float] = field(default_factory=dict)
    status: float = 0.0
    producing: bool = False
    org_id: int | None = None
    disposition: dict[str, float] = field(default_factory=dict)
    learning_rate: float = 0.1
    risk_aversion: float = 0.0
    local_norm: float = 0.5
    exchange_history: list[tuple] = field(default_factory=list)
    activity_level: float = 0.5
    perception_noise: float = 0.2
    last_event_time: float = 0.0
    proposal_cooldown_until: float = 0.0
    proposal_failures: int = 0


@dataclass
class Organization:
    id: int
    members: set[int] = field(default_factory=set)
    rules: dict[str, float] = field(default_factory=dict)
    treasury: float = 0.0
    efficiency: float = 1.0
    conflict_cost: float = 0.0
    legitimacy: float = 1.0
    recent_exits: int = 0
    recent_joins: int = 0
    last_mutation_time: float = 0.0


@dataclass(order=True)
class Event:
    trigger_time: float
    type: str = field(compare=False)
    source_id: int = field(compare=False, default=0)
    target_id: int | None = field(compare=False, default=None)
    payload: dict[str, Any] = field(compare=False, default_factory=dict)


class World:
    def __init__(self) -> None:
        self.agents: dict[int, Agent] = {}
        self.orgs: dict[int, Organization] = {}
        self.event_queue: list[Event] = []
        self.clock: float = 0.0
        self.next_org_id: int = 1
        self.event_count: int = 0
        self.metrics_log: list[dict] = []
