from __future__ import annotations
from .models import Agent, World
from . import config


class ResourceLedger:
    """因果守恒审计：所有资源变更必须经过此类，禁止直接修改余额。"""

    def transfer_wealth(self, world: World, from_id: int, to_id: int, amount: float) -> bool:
        giver = world.agents[from_id]
        receiver = world.agents[to_id]
        if amount <= 0 or giver.wealth < amount:
            return False
        giver.wealth -= amount
        receiver.wealth += amount
        return True

    def produce(self, world: World, agent_id: int, energy_cost: float) -> float:
        agent = world.agents[agent_id]
        coord_factor = 1.0
        if agent.org_id is not None:
            org = world.orgs.get(agent.org_id)
            if org:
                import math
                coord_factor = 1.0 + org.rules.get('public_goods_efficiency', 0) * math.log(len(org.members) + 1)
        wealth_gain = energy_cost * config.PRODUCTION_EFFICIENCY * coord_factor
        agent.wealth += wealth_gain
        agent.producing = False
        return wealth_gain

    def regen_energy(self, agent: Agent, elapsed: float) -> None:
        agent.energy = min(agent.max_energy, agent.energy + agent.regen_rate * elapsed)

    def tax_income(self, world: World, agent_id: int, income: float) -> float:
        agent = world.agents[agent_id]
        if agent.org_id is None:
            return income
        org = world.orgs.get(agent.org_id)
        if not org:
            return income
        tax = income * org.rules.get('tax_rate', 0)
        org.treasury += tax
        return income - tax
