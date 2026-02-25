from __future__ import annotations
"""组织管理：成立、加入、退出、解散、制度突变。"""
import math
import random
from .models import Organization, Event, World
from . import config


def calculate_management_cost(org: Organization) -> float:
    """计算组织管理成本（与规模和效率相关）"""
    size = len(org.members)
    if size == 0:
        return 0.0

    # 修复4：简化管理成本公式，移除效率倒数放大（效率低不再导致成本爆炸）
    cost = config.ORG_BASE_MANAGEMENT_COST * size * math.log(size + 1)
    return cost


def handle_org_tax_collection(world: World, org: Organization) -> None:
    """组织税收征收 + 维护成本扣除 + 按需再分配"""
    from .agent_engine import compute_ev_produce

    if len(org.members) == 0:
        return

    total_tax = 0.0

    # 1. 征税
    for member_id in list(org.members):
        agent = world.agents.get(member_id)
        if not agent:
            continue
        production = compute_ev_produce(agent, world)
        tax = org.rules['tax_rate'] * production
        tax = min(tax, agent.wealth)  # 不能扣除超过现有财富
        agent.wealth = max(0, agent.wealth - tax)
        total_tax += tax

    # 2. 扣除管理成本
    management_cost = calculate_management_cost(org)
    net_tax = total_tax - management_cost

    if net_tax < 0:
        # 入不敷出，组织腐化
        org.efficiency *= 0.9
        org.legitimacy *= 0.9
        org.treasury += total_tax  # 全部用于维持，无法再分配
        return

    # 3. 按需再分配（劫富济贫）
    redistribution_pool = net_tax * org.rules['redistribution_ratio']

    # 计算组织平均财富
    avg_wealth = sum(world.agents[m].wealth for m in org.members if m in world.agents) / len(org.members)

    # 计算总贫困度
    total_poverty = sum(max(0, avg_wealth - world.agents[m].wealth)
                       for m in org.members if m in world.agents)

    if total_poverty > 0:
        for member_id in list(org.members):
            agent = world.agents.get(member_id)
            if not agent:
                continue
            poverty_score = max(0, avg_wealth - agent.wealth)
            share = redistribution_pool * (poverty_score / total_poverty)
            agent.wealth += share

    # 4. 剩余进国库
    org.treasury += net_tax * (1 - org.rules['redistribution_ratio'])


def handle_org_proposal(world: World, event: Event) -> None:
    """Agent 发起组织提议 → 候选成员独立 EV 决策。"""
    from .agent_engine import compute_ev_join, compute_ev_outside
    source = world.agents.get(event.source_id)
    if not source or source.org_id is not None:
        return
    candidates = event.payload.get('candidates', [])

    # 新组织从现有组织中学习规则（如果有的话）
    import random
    if world.orgs:
        template_org = random.choice(list(world.orgs.values()))
        initial_rules = dict(template_org.rules)
    else:
        initial_rules = dict(config.DEFAULT_RULES)

    # 构建假设 org
    hypo_members = {source.id} | set(candidates)
    hypo_org = Organization(
        id=-1,
        members=hypo_members,
        rules=initial_rules,
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
    import random
    org_id = world.next_org_id
    world.next_org_id += 1

    # 新组织从现有组织中学习规则（如果有的话），并加入随机扰动促进分化
    if world.orgs:
        template_org = random.choice(list(world.orgs.values()))
        initial_rules = dict(template_org.rules)
    else:
        initial_rules = dict(config.DEFAULT_RULES)
    # 随机扰动：每个可突变参数随机偏移，再分配比率用更大扰动促进分化
    for key in config.MUTATABLE_KEYS:
        if key in initial_rules:
            noise_range = 0.25 if key == 'redistribution_ratio' else 0.15
            noise = random.uniform(-noise_range, noise_range)
            initial_rules[key] = max(config.RULES_MIN.get(key, 0),
                                     min(config.RULES_MAX.get(key, 1),
                                         initial_rules[key] + noise))

    org = Organization(
        id=org_id,
        members=set(member_ids),
        rules=initial_rules,
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


def _apply_org_decay(org: Organization, world: World) -> None:
    """应用组织腐化机制：渐进式衰减 + 路径依赖"""
    # 1. 乘法衰减（渐进式，不是断崖）
    org.efficiency *= config.EFFICIENCY_DECAY_BASE
    org.legitimacy *= config.LEGITIMACY_DECAY_BASE

    # 2. 规模惩罚（官僚化）
    size_penalty = config.EFFICIENCY_SIZE_PENALTY * math.log(len(org.members) + 1)
    org.efficiency *= (1 - size_penalty)

    # 3. 冲突累积影响效率
    if len(org.members) > 0:
        avg_w = sum(world.agents[m].wealth for m in org.members if m in world.agents) / len(org.members)
        if avg_w > 0 and org.conflict_cost > 0:
            conflict_penalty = min(0.1, org.conflict_cost / (avg_w * 200))
            org.efficiency *= (1 - conflict_penalty)

    # 4. 高税收降低合法性
    tax_penalty = org.rules.get('tax_rate', 0) * 0.05
    org.legitimacy *= (1 - tax_penalty)

    # 5. 内部不平等降低合法性
    if len(org.members) > 1:
        wealths = [world.agents[m].wealth for m in org.members if m in world.agents]
        if wealths:
            avg = sum(wealths) / len(wealths)
            if avg > 0:
                variance = sum((w - avg) ** 2 for w in wealths) / len(wealths)
                inequality = variance / (avg ** 2)
                inequality_penalty = config.LEGITIMACY_INEQUALITY_PENALTY * inequality
                org.legitimacy *= (1 - inequality_penalty)

    # 6. 确保不低于最小值
    org.efficiency = max(0.2, org.efficiency)
    org.legitimacy = max(0.2, org.legitimacy)


def handle_rule_mutation(world: World, event: Event) -> None:
    """成员痛点驱动的制度突变 + 改革风险"""
    from .agent_engine import compute_ev_join, effective_power
    org = world.orgs.get(event.target_id)
    if not org or len(org.members) == 0:
        return

    # 记录改革前效率
    old_efficiency = org.efficiency

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
    mutation_happened = False
    for key in config.MUTATABLE_KEYS:
        if key in grievances and abs(grievances[key]) > total_weight * config.GRIEVANCE_THRESHOLD:
            direction = 1 if grievances[key] > 0 else -1
            org.rules[key] += direction * config.MUTATION_STEP
            org.rules[key] = max(config.RULES_MIN.get(key, 0),
                                 min(config.RULES_MAX.get(key, 1), org.rules[key]))
            mutation_happened = True

    # Step 3: 改革结果（有风险）
    if mutation_happened:
        import random
        # 改革成功概率与当前效率相关（效率越低越难成功）
        success_prob = 0.3 + 0.5 * org.efficiency
        if random.random() < success_prob:
            # 成功：效率提升
            org.efficiency = min(1.0, org.efficiency + config.MUTATION_SUCCESS_BOOST)
            org.legitimacy = min(1.0, org.legitimacy + 0.1)
        else:
            # 失败：效率下降
            org.efficiency = max(0.2, org.efficiency - config.MUTATION_FAILURE_PENALTY)
            org.legitimacy = max(0.2, org.legitimacy - 0.05)

    org.conflict_cost = 0.0
    org.recent_exits = 0
    org.recent_joins = 0
    org.last_mutation_time = world.clock


def _compute_grievance(member, org, world):
    """计算成员最大痛点：哪个参数变一点对我 EV 提升最大。"""
    from .agent_engine import compute_ev_join
    current_ev = compute_ev_join(member, org, world)
    max_gain = float('-inf')  # 改为负无穷，即使所有变化都是负收益也要选择最优方向
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
    """检查所有 org 是否需要触发制度突变（由 metrics 周期调用）+ 组织解散机制 + 税收征收。"""
    import heapq
    for org in list(world.orgs.values()):
        if len(org.members) == 0:
            continue

        # 税收征收 + 维护成本 + 再分配
        handle_org_tax_collection(world, org)

        # 应用组织腐化机制
        _apply_org_decay(org, world)

        # 检查是否应该解散（效率过低）
        if org.efficiency < config.DISSOLUTION_THRESHOLD:
            # 组织解散：所有成员退出
            for mid in list(org.members):
                if mid in world.agents:
                    world.agents[mid].org_id = None
            org.members.clear()
            del world.orgs[org.id]
            continue

        avg_w = sum(world.agents[m].wealth for m in org.members if m in world.agents) / max(len(org.members), 1)

        # 新增：检查成员痛点，如果有足够多成员不满就触发改革
        grievance_count = 0
        for mid in org.members:
            member = world.agents.get(mid)
            if not member:
                continue
            pain_key, pain_dir = _compute_grievance(member, org, world)
            if pain_key and abs(pain_dir) > 0:
                grievance_count += 1

        # 如果超过 30% 成员有痛点，触发改革
        grievance_ratio = grievance_count / max(len(org.members), 1)

        should_mutate = (
            grievance_ratio > 0.3  # 新增：30% 成员不满就改革
            or org.efficiency < (1 - config.EFFICIENCY_THRESHOLD)
            or (org.recent_exits / max(len(org.members), 1)) > config.MIGRATION_THRESHOLD
            or org.conflict_cost > avg_w * 0.5
            or org.legitimacy < config.LEGITIMACY_THRESHOLD
        )

        if should_mutate and (world.clock - org.last_mutation_time) > 2.0:  # 降低到 2 虚拟时间单位
            heapq.heappush(world.event_queue, Event(
                trigger_time=world.clock + 0.1,
                type='rule_mutation',
                target_id=org.id,
            ))
            org.last_mutation_time = world.clock
