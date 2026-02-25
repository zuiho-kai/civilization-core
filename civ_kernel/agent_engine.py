from __future__ import annotations
"""Agent 行为逻辑：wake_up 决策 + Produce/Exchange/Coerce 执行。"""
import math
import random
from .models import Agent, Event, World
from . import config


# === Power 计算 ===

def effective_power(agent: Agent, world: World) -> float:
    base = config.POWER_A1 * agent.energy + config.POWER_A2 * agent.wealth
    org_mult = 1.0
    if agent.org_id is not None:
        org = world.orgs.get(agent.org_id)
        if org:
            sz = len(org.members)
            org_mult = (1 + config.POWER_B1 * math.log(sz + 1)) / (1 + config.POWER_B2 * sz)
    return max(0.01, base * org_mult)


# === EV 计算 ===

def compute_ev_produce(agent: Agent, world: World) -> float:
    cost = min(agent.energy, config.PRODUCTION_ENERGY_COST)
    tax = 0.0
    coord = 1.0
    if agent.org_id is not None:
        org = world.orgs.get(agent.org_id)
        if org:
            tax = org.rules.get('tax_rate', 0)
            coord = 1.0 + org.rules.get('public_goods_efficiency', 0) * math.log(len(org.members) + 1)
    return cost * config.PRODUCTION_EFFICIENCY * coord * (1 - tax)


def compute_ev_exchange(agent: Agent, world: World) -> float:
    if not agent.neighbors:
        return 0.0
    best_gap = 0.0
    for nb_id, trust in agent.neighbors.items():
        nb = world.agents.get(nb_id)
        if not nb or nb.producing:
            continue
        gap = _perceived_price_gap(agent, nb, trust)
        if gap > best_gap:
            best_gap = gap
    return best_gap * agent.wealth * 0.5


def compute_ev_coerce(agent: Agent, target: Agent, world: World) -> float:
    power_a = effective_power(agent, world)
    noise = random.uniform(1 - agent.perception_noise, 1 + agent.perception_noise)
    perceived_b = effective_power(target, world) * noise
    p_success = power_a / (power_a + perceived_b)
    loot = min(target.wealth * config.LOOT_RATIO, agent.energy * config.LOOT_EFFICIENCY)
    energy_cost = config.BASE_COERCE_ENERGY
    wealth_cost = config.BASE_COERCE_WEALTH
    if agent.org_id is not None:
        org = world.orgs.get(agent.org_id)
        if org:
            sz = len(org.members)
            wealth_cost *= (1 + (sz ** 1.5) / config.COERCE_SCALE_FACTOR)
    penalty = _coerce_fail_penalty(agent, target, world)
    return p_success * loot - (1 - p_success) * penalty - energy_cost - wealth_cost


def compute_ev_join(agent: Agent, org, world: World) -> float:
    sz = len(org.members)
    rules = org.rules
    production = compute_ev_produce(agent, world)
    e_economic = ((1 - rules.get('tax_rate', 0)) * production
                  + org.treasury * rules.get('redistribution_ratio', 0) / max(sz, 1)
                  + rules.get('public_goods_efficiency', 0) * math.log(sz + 1) * production)
    e_security = 0.1 * agent.wealth  # 简化：组织提供 10% 保护
    c_tax = rules.get('tax_rate', 0) * production
    c_coercion = 0.1 * rules.get('punishment_severity', 0) * agent.wealth
    c_exit = rules.get('exit_penalty', 0) * agent.wealth * 0.1
    return e_economic + e_security - c_tax - c_coercion - c_exit


def compute_ev_outside(agent: Agent, world: World) -> float:
    production = compute_ev_produce(agent, world)
    coerce_risk = 0.15 * agent.wealth  # 简化
    return production - coerce_risk


# === 内部工具 ===

def _perceived_price_gap(agent: Agent, neighbor: Agent, trust: float) -> float:
    max_w = max(agent.wealth, neighbor.wealth, 1.0)
    gap_raw = abs(agent.wealth - neighbor.wealth) / max_w
    d = agent.disposition
    gap_gain = gap_raw
    gap_norm = agent.local_norm * gap_raw
    gap_trust = 0.0 if trust > config.TRIBE_THRESHOLD else -1.0
    gap = (d.get('gain', 0.33) * gap_gain
           + d.get('norm', 0.33) * gap_norm
           + d.get('trust', 0.33) * gap_trust)
    return max(0.0, gap * (1 - agent.risk_aversion))


def _coerce_fail_penalty(agent: Agent, target: Agent, world: World) -> float:
    power_a = effective_power(agent, world)
    power_b = effective_power(target, world)
    r_retaliation = (power_b / (power_a + power_b)) * config.COUNTER_SEVERITY * agent.wealth
    s_institution = 0.0
    if agent.org_id is not None and agent.org_id == target.org_id:
        org = world.orgs.get(agent.org_id)
        if org:
            enforce_prob = 1 - org.rules.get('internal_coercion_tolerance', 0.2)
            s_institution = enforce_prob * org.rules.get('punishment_severity', 0.3) * agent.wealth
    return r_retaliation + s_institution


def _update_disposition(agent: Agent, outcome: float, dominant_dim: str) -> None:
    for dim in ('gain', 'norm', 'trust'):
        contrib = 1.0 if dim == dominant_dim else 0.0
        agent.disposition[dim] += agent.learning_rate * outcome * contrib
    total = sum(max(0.01, v) for v in agent.disposition.values())
    for dim in agent.disposition:
        agent.disposition[dim] = max(0.01, agent.disposition[dim]) / total


def _schedule(world: World, event: Event) -> None:
    import heapq
    heapq.heappush(world.event_queue, event)


def _avg_neighbor_wealth(agent: Agent, world: World) -> float:
    if not agent.neighbors:
        return agent.wealth
    total = sum(world.agents[n].wealth for n in agent.neighbors if n in world.agents)
    return total / len(agent.neighbors)


# === 事件处理函数 ===

def handle_wake_up(world: World, event: Event) -> None:
    agent = world.agents.get(event.source_id)
    if not agent:
        return
    # 回复 energy
    from .resource import ResourceLedger
    ledger = ResourceLedger()
    elapsed = world.clock - agent.last_event_time
    ledger.regen_energy(agent, elapsed)
    agent.last_event_time = world.clock

    if agent.producing:
        _schedule_next_wakeup(world, agent)
        return

    # 决策：evaluate all options
    ev_prod = compute_ev_produce(agent, world)
    ev_exch = compute_ev_exchange(agent, world)

    # 找最佳 coerce 目标
    ev_coerce_best = -999
    coerce_target = None
    for nb_id in agent.neighbors:
        nb = world.agents.get(nb_id)
        if not nb or nb.wealth < agent.wealth * config.COERCE_WEALTH_RATIO:
            continue
        ev_c = compute_ev_coerce(agent, nb, world)
        if ev_c > ev_coerce_best:
            ev_coerce_best = ev_c
            coerce_target = nb

    # 选最优行为
    best = max(ev_prod, ev_exch, ev_coerce_best)
    if best == ev_coerce_best and coerce_target and ev_coerce_best > 0:
        _do_coerce(world, agent, coerce_target)
    elif best == ev_exch and ev_exch > 0:
        _do_exchange(world, agent)
    else:
        _do_produce(world, agent)

    # 组织相关决策
    _check_org_decisions(world, agent)
    _schedule_next_wakeup(world, agent)


def handle_produce_complete(world: World, event: Event) -> None:
    agent = world.agents.get(event.source_id)
    if not agent:
        return
    from .resource import ResourceLedger
    ledger = ResourceLedger()
    energy_cost = event.payload.get('energy_cost', config.PRODUCTION_ENERGY_COST)
    wealth_gain = ledger.produce(world, agent.id, energy_cost)
    wealth_gain = ledger.tax_income(world, agent.id, wealth_gain)


def handle_exchange_request(world: World, event: Event) -> None:
    source = world.agents.get(event.source_id)
    target = world.agents.get(event.target_id)
    if not source or not target:
        return
    if target.producing:
        return
    # 估值：基于本地邻居均值的稀缺度定价（不同区域自然分化）
    src_local_avg = _avg_neighbor_wealth(source, world)
    tgt_local_avg = _avg_neighbor_wealth(target, world)
    # 报价 = 基础比例 × 本地稀缺度修正
    offer = source.wealth * 0.1 * (1 + 0.5 * (source.wealth / max(src_local_avg, 0.1) - 1))
    valuation = target.wealth * 0.1 * (1 + 0.5 * (target.wealth / max(tgt_local_avg, 0.1) - 1))
    offer = max(0.01, offer)
    valuation = max(0.01, valuation)
    spread = abs(offer - valuation)
    # 成交判断
    trust_ab = source.neighbors.get(target.id, 0)
    accept_threshold = 0.3 * (1 - trust_ab)
    if spread < max(offer, valuation) * (accept_threshold + 0.1):
        # 成交：实际成交价记录到 history（用于价格方差度量）
        price = (offer + valuation) / 2
        from .resource import ResourceLedger
        ledger = ResourceLedger()
        transfer_amount = min(price * 0.5, source.wealth, target.wealth)
        if transfer_amount > 0:
            ledger.transfer_wealth(world, source.id, target.id, transfer_amount)
            ledger.transfer_wealth(world, target.id, source.id, transfer_amount)
            delta_w = transfer_amount * 0.05
            source.wealth += delta_w
            target.wealth += delta_w
            from .network import update_trust
            update_trust(world, source.id, target.id, 0.02)
            source.exchange_history.append((target.id, True, price))
            target.exchange_history.append((source.id, True, price))
            _update_disposition(source, delta_w, 'gain')
            _update_disposition(target, delta_w, 'gain')
            # 更新 local_norm
            source.local_norm = config.EMA_ALPHA + (1 - config.EMA_ALPHA) * source.local_norm
            target.local_norm = config.EMA_ALPHA + (1 - config.EMA_ALPHA) * target.local_norm
    else:
        # 拒绝
        source.exchange_history.append((target.id, False, 0))
        source.local_norm = (1 - config.EMA_ALPHA) * source.local_norm


def handle_coerce_attempt(world: World, event: Event) -> None:
    source = world.agents.get(event.source_id)
    target = world.agents.get(event.target_id)
    if not source or not target:
        return
    _do_coerce_settle(world, source, target)


# === 行为执行 ===

def _do_produce(world: World, agent: Agent) -> None:
    cost = min(agent.energy, config.PRODUCTION_ENERGY_COST)
    if cost <= 0:
        return
    agent.energy -= cost
    agent.producing = True
    duration = config.PRODUCTION_DURATION_BASE / (1 + agent.energy)
    _schedule(world, Event(
        trigger_time=world.clock + duration,
        type='produce_complete',
        source_id=agent.id,
        payload={'energy_cost': cost},
    ))


def _do_exchange(world: World, agent: Agent) -> None:
    if agent.energy < config.EXCHANGE_ENERGY_COST:
        return
    # 选择最佳交易对象
    candidates = []
    for nb_id, trust in agent.neighbors.items():
        nb = world.agents.get(nb_id)
        if nb and not nb.producing:
            gap = _perceived_price_gap(agent, nb, trust)
            candidates.append((gap, nb_id))
    if not candidates:
        return
    candidates.sort(reverse=True)
    for _, nb_id in candidates[:config.MAX_EXCHANGE_ATTEMPTS]:
        agent.energy -= config.EXCHANGE_ENERGY_COST
        _schedule(world, Event(
            trigger_time=world.clock + 0.1,
            type='exchange_request',
            source_id=agent.id,
            target_id=nb_id,
        ))


def _do_coerce(world: World, agent: Agent, target: Agent) -> None:
    if agent.wealth < config.BASE_COERCE_WEALTH or agent.energy < config.BASE_COERCE_ENERGY:
        return
    _schedule(world, Event(
        trigger_time=world.clock + 0.5,
        type='coerce_attempt',
        source_id=agent.id,
        target_id=target.id,
    ))


def _do_coerce_settle(world: World, source: Agent, target: Agent) -> None:
    from .resource import ResourceLedger
    from .network import update_trust
    ledger = ResourceLedger()
    # 代价
    energy_cost = config.BASE_COERCE_ENERGY
    wealth_cost = config.BASE_COERCE_WEALTH
    if source.org_id is not None:
        org = world.orgs.get(source.org_id)
        if org:
            sz = len(org.members)
            wealth_cost *= (1 + (sz ** 1.5) / config.COERCE_SCALE_FACTOR)
            # org 补贴
            share = org.rules.get('enforcement_cost_share', 0)
            org_pays = wealth_cost * share
            if org.treasury >= org_pays:
                org.treasury -= org_pays
                wealth_cost -= org_pays
    source.energy = max(0, source.energy - energy_cost)
    # 成功判定
    power_a = effective_power(source, world)
    power_b = effective_power(target, world)
    p_actual = power_a / (power_a + power_b)
    if random.random() < p_actual:
        # 成功
        loot = min(target.wealth * config.LOOT_RATIO, source.energy * config.LOOT_EFFICIENCY)
        loot = min(loot, target.wealth)
        if loot > 0:
            ledger.transfer_wealth(world, target.id, source.id, loot)
        source.wealth -= min(wealth_cost, source.wealth)
        update_trust(world, target.id, source.id, -0.3)
        # 邻居声誉惩罚
        for nb_id in list(target.neighbors.keys()):
            if nb_id != source.id and nb_id in world.agents:
                update_trust(world, nb_id, source.id, -0.05)
        # org conflict cost
        if source.org_id is not None:
            org = world.orgs.get(source.org_id)
            if org:
                org.conflict_cost += wealth_cost
    else:
        # 失败
        source.wealth -= min(wealth_cost, source.wealth)
        penalty = _coerce_fail_penalty(source, target, world)
        source.wealth = max(0, source.wealth - penalty)
        update_trust(world, target.id, source.id, -0.2)


def _check_org_decisions(world: World, agent: Agent) -> None:
    """检查 Agent 是否要退出/加入/提议组织。"""
    from .org import leave_org
    ev_out = compute_ev_outside(agent, world)

    # 已在 org → 考虑退出
    if agent.org_id is not None:
        org = world.orgs.get(agent.org_id)
        if org:
            ev_in = compute_ev_join(agent, org, world)
            if ev_out - ev_in > config.EXIT_THRESHOLD:
                leave_org(world, agent.id)
        return

    # 无 org → 考虑加入邻居的 org
    for nb_id in agent.neighbors:
        nb = world.agents.get(nb_id)
        if nb and nb.org_id is not None:
            org = world.orgs.get(nb.org_id)
            if org:
                avg_trust = sum(agent.neighbors.get(m, 0) for m in org.members) / max(len(org.members), 1)
                if avg_trust >= org.rules.get('entry_barrier', 0.3):
                    ev_in = compute_ev_join(agent, org, world)
                    if ev_in - ev_out > config.JOIN_THRESHOLD:
                        from .org import join_org
                        join_org(world, agent.id, org.id)
                        return

    # 无 org 且没找到可加入的 → 考虑发起提议
    if world.clock < agent.proposal_cooldown_until:
        return
    high_trust_nbs = [n for n, t in agent.neighbors.items()
                      if t > config.PROPOSE_TRUST_THRESHOLD
                      and world.agents.get(n) and world.agents[n].org_id is None]
    if len(high_trust_nbs) < config.MIN_ORG_SIZE - 1:
        return
    _schedule(world, Event(
        trigger_time=world.clock + 0.2,
        type='org_proposal',
        source_id=agent.id,
        payload={'candidates': high_trust_nbs},
    ))


def _schedule_next_wakeup(world: World, agent: Agent) -> None:
    interval = config.BASE_INTERVAL / (1 + math.log(agent.wealth + 1))
    jitter = random.uniform(-0.5, 0.5)
    _schedule(world, Event(
        trigger_time=world.clock + max(0.5, interval + jitter),
        type='wake_up',
        source_id=agent.id,
    ))
