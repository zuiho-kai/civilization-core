"""测试激励层：验证富人和穷人的税率偏好是否正确"""
import sys
import io
import random

# Windows GBK 编码兼容
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith('gbk'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from civ_kernel.models import Agent, Organization, World
from civ_kernel.agent_engine import compute_ev_join, compute_ev_produce
from civ_kernel.network import generate_ws_graph
from civ_kernel import config


def create_test_world():
    """创建测试世界"""
    world = World()
    graph = generate_ws_graph(20, 4, 0.15)

    for i in range(20):
        agent = Agent(
            id=i,
            wealth=config.INIT_WEALTH * random.uniform(0.5, 1.5),
            energy=config.INIT_ENERGY,
            max_energy=config.MAX_ENERGY,
            regen_rate=config.REGEN_RATE,
            neighbors=dict(graph[i]),
            disposition={'gain': 0.4, 'norm': 0.3, 'trust': 0.3},
            learning_rate=0.1,
            risk_aversion=0.5,
            local_norm=0.5,
            activity_level=0.8,
            perception_noise=0.2,
        )
        world.agents[i] = agent

    return world


def test_poor_wants_high_tax():
    """测试：穷人应该想提高税率"""
    print("=" * 60)
    print("测试 1: 穷人是否想提高税率")
    print("=" * 60)

    world = create_test_world()

    # 创建测试组织
    members = set(range(10))
    org = Organization(
        id=1,
        members=members,
        rules=dict(config.DEFAULT_RULES),
        treasury=100.0,
        efficiency=0.8,
        legitimacy=0.8,
    )

    # 找最穷的成员
    poor_agent = min((world.agents[m] for m in members), key=lambda a: a.wealth)

    print(f"\n穷人 Agent {poor_agent.id}: wealth={poor_agent.wealth:.1f}")
    print(f"当前税率: {org.rules['tax_rate']*100:.0f}%")
    print(f"当前再分配: {org.rules['redistribution_ratio']*100:.0f}%")

    # 当前 EV
    current_ev = compute_ev_join(poor_agent, org, world)
    print(f"\n当前 EV: {current_ev:.3f}")

    # 提高税率
    org_higher = Organization(
        id=1, members=members,
        rules={**org.rules, 'tax_rate': org.rules['tax_rate'] + 0.05},
        treasury=org.treasury, efficiency=org.efficiency, legitimacy=org.legitimacy
    )
    higher_ev = compute_ev_join(poor_agent, org_higher, world)
    print(f"提高税率 5% 后 EV: {higher_ev:.3f}")
    print(f"EV 变化: {higher_ev - current_ev:+.3f}")

    if higher_ev > current_ev:
        print("✅ 通过：穷人支持提高税率")
        return True
    else:
        print("❌ 失败：穷人反对提高税率")
        return False


def test_rich_wants_low_tax():
    """测试：富人应该想降低税率"""
    print("\n" + "=" * 60)
    print("测试 2: 富人是否想降低税率")
    print("=" * 60)

    world = create_test_world()

    # 创建测试组织
    members = set(range(10))
    org = Organization(
        id=1,
        members=members,
        rules=dict(config.DEFAULT_RULES),
        treasury=100.0,
        efficiency=0.8,
        legitimacy=0.8,
    )

    # 找最富的成员
    rich_agent = max((world.agents[m] for m in members), key=lambda a: a.wealth)

    print(f"\n富人 Agent {rich_agent.id}: wealth={rich_agent.wealth:.1f}")
    print(f"当前税率: {org.rules['tax_rate']*100:.0f}%")
    print(f"当前再分配: {org.rules['redistribution_ratio']*100:.0f}%")

    # 当前 EV
    current_ev = compute_ev_join(rich_agent, org, world)
    print(f"\n当前 EV: {current_ev:.3f}")

    # 降低税率
    org_lower = Organization(
        id=1, members=members,
        rules={**org.rules, 'tax_rate': org.rules['tax_rate'] - 0.05},
        treasury=org.treasury, efficiency=org.efficiency, legitimacy=org.legitimacy
    )
    lower_ev = compute_ev_join(rich_agent, org_lower, world)
    print(f"降低税率 5% 后 EV: {lower_ev:.3f}")
    print(f"EV 变化: {lower_ev - current_ev:+.3f}")

    if lower_ev > current_ev:
        print("✅ 通过：富人支持降低税率")
        return True
    else:
        print("❌ 失败：富人反对降低税率")
        return False


def test_redistribution_benefit():
    """测试：再分配收益应该显著大于税收成本（对穷人）"""
    print("\n" + "=" * 60)
    print("测试 3: 再分配收益是否足够大")
    print("=" * 60)

    world = create_test_world()

    members = set(range(10))
    org = Organization(
        id=1,
        members=members,
        rules=dict(config.DEFAULT_RULES),
        treasury=100.0,
        efficiency=0.8,
        legitimacy=0.8,
    )

    poor_agent = min((world.agents[m] for m in members), key=lambda a: a.wealth)

    print(f"\n穷人 Agent {poor_agent.id}: wealth={poor_agent.wealth:.1f}")

    # 计算税收成本
    production = compute_ev_produce(poor_agent, world)
    tax_cost = org.rules['tax_rate'] * production

    # 计算再分配收益
    total_production = sum(compute_ev_produce(world.agents[m], world) for m in members)
    total_tax = org.rules['tax_rate'] * total_production
    redistribution_pool = total_tax * org.rules['redistribution_ratio']

    avg_wealth = sum(world.agents[m].wealth for m in members) / len(members)
    poverty_score = max(0, avg_wealth - poor_agent.wealth)
    total_poverty = sum(max(0, avg_wealth - world.agents[m].wealth) for m in members)

    if total_poverty > 0:
        redistribution_benefit = redistribution_pool * (poverty_score / total_poverty)
    else:
        redistribution_benefit = 0

    print(f"\n产出: {production:.3f}")
    print(f"税收成本: {tax_cost:.3f}")
    print(f"再分配收益: {redistribution_benefit:.3f}")
    print(f"净收益: {redistribution_benefit - tax_cost:+.3f}")
    print(f"收益/成本比: {redistribution_benefit / tax_cost if tax_cost > 0 else 0:.2f}x")

    if redistribution_benefit > tax_cost * 1.5:
        print("✅ 通过：再分配收益 > 税收成本的 1.5 倍")
        return True
    else:
        print("❌ 失败：再分配收益不足")
        return False


def test_grievance_direction():
    """测试：痛点方向应该与 EV 增益一致"""
    print("\n" + "=" * 60)
    print("测试 4: 痛点方向是否正确")
    print("=" * 60)

    from civ_kernel.org import _compute_grievance

    world = create_test_world()

    members = set(range(10))
    org = Organization(
        id=1,
        members=members,
        rules=dict(config.DEFAULT_RULES),
        treasury=100.0,
        efficiency=0.8,
        legitimacy=0.8,
    )

    # 测试穷人和富人
    poor_agent = min((world.agents[m] for m in members), key=lambda a: a.wealth)
    rich_agent = max((world.agents[m] for m in members), key=lambda a: a.wealth)

    all_pass = True

    for agent, label in [(poor_agent, "穷人"), (rich_agent, "富人")]:
        print(f"\n{label} Agent {agent.id}: wealth={agent.wealth:.1f}")

        pain_key, pain_dir = _compute_grievance(agent, org, world)
        print(f"痛点: {pain_key}, 方向: {pain_dir}")

        if pain_key:
            # 验证：按痛点方向改变后，EV 应该增加
            current_ev = compute_ev_join(agent, org, world)

            org_modified = Organization(
                id=1, members=members,
                rules={**org.rules, pain_key: org.rules[pain_key] + pain_dir * config.MUTATION_STEP},
                treasury=org.treasury, efficiency=org.efficiency, legitimacy=org.legitimacy
            )
            modified_ev = compute_ev_join(agent, org_modified, world)

            print(f"当前 EV: {current_ev:.3f}")
            print(f"改变后 EV: {modified_ev:.3f}")
            print(f"EV 变化: {modified_ev - current_ev:+.3f}")

            if modified_ev > current_ev:
                print(f"✅ 通过：痛点方向正确")
            else:
                print(f"❌ 失败：痛点方向错误")
                all_pass = False

    return all_pass


if __name__ == '__main__':
    random.seed(42)

    results = []
    results.append(test_poor_wants_high_tax())
    results.append(test_rich_wants_low_tax())
    results.append(test_redistribution_benefit())
    results.append(test_grievance_direction())

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"通过: {sum(results)}/{len(results)}")

    if all(results):
        print("✅ 所有测试通过！")
        sys.exit(0)
    else:
        print("❌ 部分测试失败")
        sys.exit(1)
