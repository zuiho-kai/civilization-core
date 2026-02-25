from __future__ import annotations
"""组织管理：成立、加入、退出、解散、制度突变。"""
import math
import random
from .models import Organization, Event, World
from . import config


def handle_org_proposal(world: World, event: Event) -> None:
    """Agent 发起组织提议 → 候选成员独立 EV 决策。"""
    from .agent_engine import compute_ev_join, compute_ev_outside
    source = world.agents.get(event.source_id)
    if not source or source.org_id is not None:
        return
    candidates = event.payload.get('candidates', [])
    # 构建假设 org
    hypo_members = {source.id} | set(candidates)
    hypo_org = Organization(
        id=-1,
        members=hypo_members,
        rules=dict(config.DEFAULT_RULES),
    )
    # 发起者自己先算
    ev_in = compute_ev_join(source, hypo_org, world)
    ev_out = compute_ev_outside(source, world)
    if ev_in - ev_out < config.PROPOSE_MARGIN:
        _proposal_failed(source, world)
        return
    # 候选成员独立决策
    agreed = [source.id]
    for c_id in candidates:
        c = world.agents.get(c_id)
        if not c or c.org_id is not None:
            continue
        c_ev_in = compute_ev_join(c, hypo_org, world)
        c_ev_out = compute_ev_outside(c, world)
        if c_ev_in - c_ev_out > 0:
            agreed.append(c_id)
    if len(agreed) >= config.MIN_ORG_SIZE:
        create_org(world, agreed)
        source.proposal_failures = 0
    else:
        _proposal_failed(source, world)


def _proposal_failed(source, world):
    source.proposal_failures += 1
    cooldown = config.COOLDOWN_BASE * (config.BACKOFF_FACTOR ** source.proposal_failures)
    source.proposal_cooldown_until = world.clock + cooldown


def create_org(world: World, member_ids: list[int]) -> Organization:
    org_id = world.next_org_id
    world.next_org_id += 1
    org = Organization(
        id=org_id,
        members=set(member_ids),
        rules=dict(config.DEFAULT_RULES),
        last_mutation_time=world.clock,
    )
    world.orgs[org_id] = org
    for mid in member_ids:
        agent = world.agents.get(mid)
        if agent:
            agent.org_id = org_id
    return org


def join_org(world: World, agent_id: int, org_id: int) -> None:
    agent = world.agents.get(agent_id)
    org = world.orgs.get(org_id)
    if not agent or not org:
        return
    agent.org_id = org_id
    org.members.add(agent_id)
    org.recent_joins += 1


def leave_org(world: World, agent_id: int) -> None:
    agent = world.agents.get(agent_id)
    if not agent or agent.org_id is None:
        return
    org = world.orgs.get(agent.org_id)
    if org:
        penalty = org.rules.get('exit_penalty', 0) * agent.wealth
        agent.wealth = max(0, agent.wealth - penalty)
        org.members.discard(agent_id)
        org.recent_exits += 1
        if len(org.members) < config.MIN_ORG_SIZE:
            dissolve_org(world, org.id)
    agent.org_id = None
    from .network import network_rewire
    network_rewire(world, agent_id)


def dissolve_org(world: World, org_id: int) -> None:
    org = world.orgs.get(org_id)
    if not org:
        return
    for mid in list(org.members):
        agent = world.agents.get(mid)
        if agent:
            agent.org_id = None
    del world.orgs[org_id]


def handle_rule_mutation(world: World, event: Event) -> None:
    """成员痛点驱动的制度突变。"""
    from .agent_engine import compute_ev_join, effective_power
    org = world.orgs.get(event.target_id)
    if not org or len(org.members) == 0:
        return
    # Step 1: 每个成员计算痛点
    grievances: dict[str, float] = {}
    total_weight = 0.0
    for mid in org.members:
        member = world.agents.get(mid)
        if not member:
            continue
        weight = effective_power(member, world)
        total_weight += weight
        pain_key, pain_dir = _compute_grievance(member, org, world)
        if pain_key:
            grievances[pain_key] = grievances.get(pain_key, 0) + weight * pain_dir
    if total_weight == 0:
        return
    # Step 2: 超过阈值的诉求执行
    for key in config.MUTATABLE_KEYS:
        if key in grievances and abs(grievances[key]) > total_weight * config.GRIEVANCE_THRESHOLD:
            direction = 1 if grievances[key] > 0 else -1
            org.rules[key] += direction * config.MUTATION_STEP
            org.rules[key] = max(config.RULES_MIN.get(key, 0),
                                 min(config.RULES_MAX.get(key, 1), org.rules[key]))
    org.efficiency = 1.0
    org.conflict_cost = 0.0
    org.recent_exits = 0
    org.recent_joins = 0
    org.last_mutation_time = world.clock


def _compute_grievance(member, org, world):
    """计算成员最大痛点：哪个参数变一点对我 EV 提升最大。"""
    from .agent_engine import compute_ev_join
    current_ev = compute_ev_join(member, org, world)
    max_gain = 0.0
    pain_key = None
    pain_dir = 0
    for key in config.MUTATABLE_KEYS:
        for direction in (1, -1):
            hypo_rules = dict(org.rules)
            hypo_rules[key] += direction * config.MUTATION_STEP
            hypo_rules[key] = max(config.RULES_MIN.get(key, 0),
                                  min(config.RULES_MAX.get(key, 1), hypo_rules[key]))
            hypo_org = Organization(id=org.id, members=org.members,
                                    rules=hypo_rules, treasury=org.treasury,
                                    efficiency=org.efficiency, legitimacy=org.legitimacy)
            hypo_ev = compute_ev_join(member, hypo_org, world)
            gain = hypo_ev - current_ev
            if gain > max_gain:
                max_gain = gain
                pain_key = key
                pain_dir = direction
    return pain_key, pain_dir


def check_mutation_triggers(world: World) -> None:
    """检查所有 org 是否需要触发制度突变（由 metrics 周期调用）。"""
    import heapq
    for org in list(world.orgs.values()):
        if len(org.members) == 0:
            continue
        avg_w = sum(world.agents[m].wealth for m in org.members if m in world.agents) / max(len(org.members), 1)
        should_mutate = (
            org.efficiency < (1 - config.EFFICIENCY_THRESHOLD)
            or (org.recent_exits / max(len(org.members), 1)) > config.MIGRATION_THRESHOLD
            or org.conflict_cost > avg_w * 0.5
        )
        if should_mutate and (world.clock - org.last_mutation_time) > 20:
            heapq.heappush(world.event_queue, Event(
                trigger_time=world.clock + 0.1,
                type='rule_mutation',
                target_id=org.id,
            ))
