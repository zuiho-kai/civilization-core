"""集成测试：验证政策分化和系统行为"""
import sys
import io
import pickle
import math

# Windows GBK 编码兼容
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith('gbk'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def std_dev(values):
    """计算标准差"""
    if len(values) == 0:
        return 0
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean)**2 for x in values) / len(values))


def test_policy_divergence():
    """测试：政策应该分化"""
    print("=" * 60)
    print("测试 1: 政策分化")
    print("=" * 60)

    with open('checkpoints/checkpoint_10000.pkl', 'rb') as f:
        world = pickle.load(f)

    if len(world.orgs) == 0:
        print("❌ 失败：没有组织存在")
        return False

    tax_rates = [org.rules['tax_rate'] for org in world.orgs.values()]
    redist_rates = [org.rules['redistribution_ratio'] for org in world.orgs.values()]

    print(f"\n组织数: {len(world.orgs)}")
    print(f"税率范围: {min(tax_rates):.3f} - {max(tax_rates):.3f}")
    print(f"再分配范围: {min(redist_rates):.3f} - {max(redist_rates):.3f}")
    print(f"税率标准差: {std_dev(tax_rates):.3f}")
    print(f"再分配标准差: {std_dev(redist_rates):.3f}")

    policy_combos = set((round(t, 2), round(r, 2)) for t, r in zip(tax_rates, redist_rates))
    print(f"不同政策组合数: {len(policy_combos)}")

    all_pass = True

    if std_dev(tax_rates) < 0.05:
        print("❌ 失败：税率标准差 < 0.05")
        all_pass = False
    else:
        print("✅ 通过：税率标准差 >= 0.05")

    if std_dev(redist_rates) < 0.1:
        print("❌ 失败：再分配标准差 < 0.1")
        all_pass = False
    else:
        print("✅ 通过：再分配标准差 >= 0.1")

    if len(policy_combos) < 3:
        print("❌ 失败：政策组合数 < 3")
        all_pass = False
    else:
        print("✅ 通过：政策组合数 >= 3")

    return all_pass


def test_rich_vs_poor_orgs():
    """测试：富人组织税率应该低于穷人组织"""
    print("\n" + "=" * 60)
    print("测试 2: 富人组织 vs 穷人组织")
    print("=" * 60)

    with open('checkpoints/checkpoint_10000.pkl', 'rb') as f:
        world = pickle.load(f)

    if len(world.orgs) < 2:
        print("❌ 失败：组织数量不足")
        return False

    orgs_by_wealth = []
    for org in world.orgs.values():
        if len(org.members) == 0:
            continue
        avg_wealth = sum(world.agents[m].wealth for m in org.members if m in world.agents) / len(org.members)
        orgs_by_wealth.append((avg_wealth, org))

    if len(orgs_by_wealth) < 2:
        print("❌ 失败：有效组织数量不足")
        return False

    orgs_by_wealth.sort()

    # 取最穷和最富的 1/3
    n = len(orgs_by_wealth)
    poor_orgs = orgs_by_wealth[:max(1, n//3)]
    rich_orgs = orgs_by_wealth[-max(1, n//3):]

    avg_poor_tax = sum(org.rules['tax_rate'] for _, org in poor_orgs) / len(poor_orgs)
    avg_rich_tax = sum(org.rules['tax_rate'] for _, org in rich_orgs) / len(rich_orgs)

    print(f"\n穷人组织平均财富: {sum(w for w, _ in poor_orgs) / len(poor_orgs):.1f}")
    print(f"穷人组织平均税率: {avg_poor_tax*100:.1f}%")
    print(f"\n富人组织平均财富: {sum(w for w, _ in rich_orgs) / len(rich_orgs):.1f}")
    print(f"富人组织平均税率: {avg_rich_tax*100:.1f}%")

    if avg_poor_tax > avg_rich_tax:
        print("\n✅ 通过：穷人组织税率 > 富人组织税率")
        return True
    else:
        print("\n❌ 失败：穷人组织税率 <= 富人组织税率")
        return False


def test_org_dynamics():
    """测试：组织动态（生死更替）"""
    print("\n" + "=" * 60)
    print("测试 3: 组织动态")
    print("=" * 60)

    checkpoints = [2000, 4000, 6000, 8000, 10000]
    org_counts = []

    for cp in checkpoints:
        try:
            with open(f'checkpoints/checkpoint_{cp}.pkl', 'rb') as f:
                world = pickle.load(f)
                org_counts.append(len(world.orgs))
        except FileNotFoundError:
            print(f"警告：checkpoint_{cp}.pkl 不存在")
            continue

    if len(org_counts) < 2:
        print("❌ 失败：checkpoint 数量不足")
        return False

    print(f"\n组织数量变化: {org_counts}")
    print(f"最小: {min(org_counts)}, 最大: {max(org_counts)}")
    print(f"变化幅度: {max(org_counts) - min(org_counts)}")

    if max(org_counts) - min(org_counts) >= 2:
        print("✅ 通过：组织数量有显著变化")
        return True
    else:
        print("❌ 失败：组织数量变化不足")
        return False


def test_policy_details():
    """测试：详细政策分布"""
    print("\n" + "=" * 60)
    print("测试 4: 详细政策分布")
    print("=" * 60)

    with open('checkpoints/checkpoint_10000.pkl', 'rb') as f:
        world = pickle.load(f)

    print(f"\n组织数: {len(world.orgs)}\n")

    for org_id, org in sorted(world.orgs.items()):
        if len(org.members) == 0:
            continue

        avg_wealth = sum(world.agents[m].wealth for m in org.members if m in world.agents) / len(org.members)

        print(f"组织 {org_id}:")
        print(f"  成员: {len(org.members)}, 平均财富: {avg_wealth:.1f}")
        print(f"  税率: {org.rules['tax_rate']*100:.1f}%, 再分配: {org.rules['redistribution_ratio']*100:.1f}%")
        print(f"  效率: {org.efficiency:.3f}, 合法性: {org.legitimacy:.3f}")

    return True


if __name__ == '__main__':
    results = []

    try:
        results.append(test_policy_divergence())
        results.append(test_rich_vs_poor_orgs())
        results.append(test_org_dynamics())
        results.append(test_policy_details())

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

    except FileNotFoundError as e:
        print(f"\n❌ 错误：找不到 checkpoint 文件")
        print(f"请先运行模拟: python -m civ_kernel.main")
        sys.exit(1)
