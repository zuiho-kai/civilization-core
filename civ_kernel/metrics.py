from __future__ import annotations
from .models import World


def compute_gini(agents_dict: dict) -> float:
    wealths = sorted(a.wealth for a in agents_dict.values())
    n = len(wealths)
    if n == 0 or sum(wealths) == 0:
        return 0.0
    cumulative = 0.0
    weighted_sum = 0.0
    for i, w in enumerate(wealths):
        cumulative += w
        weighted_sum += (i + 1) * w
    mean_w = cumulative / n
    if mean_w == 0:
        return 0.0
    return (2 * weighted_sum) / (n * cumulative) - (n + 1) / n


def compute_price_variance(world: World) -> float:
    # 按 org 分区域，统计各区域平均成交价
    region_prices: dict[int | None, list[float]] = {}
    for agent in world.agents.values():
        key = agent.org_id
        for hist in agent.exchange_history[-10:]:
            if len(hist) >= 3:
                region_prices.setdefault(key, []).append(hist[2])
    if len(region_prices) < 2:
        return 0.0
    avgs = [sum(ps) / len(ps) for ps in region_prices.values() if ps]
    if len(avgs) < 2:
        return 0.0
    mean_avg = sum(avgs) / len(avgs)
    return sum((a - mean_avg) ** 2 for a in avgs) / len(avgs)


def snapshot(world: World) -> dict:
    gini = compute_gini(world.agents)
    n_orgs = len(world.orgs)
    total_wealth = sum(a.wealth for a in world.agents.values())
    avg_wealth = total_wealth / len(world.agents) if world.agents else 0
    mutation_count = sum(1 for o in world.orgs.values() if o.last_mutation_time > 0)
    return {
        'time': world.clock,
        'events': world.event_count,
        'gini': round(gini, 4),
        'n_orgs': n_orgs,
        'total_wealth': round(total_wealth, 2),
        'avg_wealth': round(avg_wealth, 2),
        'n_agents': len(world.agents),
        'price_var': round(compute_price_variance(world), 4),
        'mutation_count': mutation_count,
    }


def print_summary(metrics_log: list[dict]) -> None:
    if not metrics_log:
        print("无指标数据")
        return
    print(f"\n{'='*60}")
    print(f"模拟结果摘要（共 {len(metrics_log)} 个快照）")
    print(f"{'='*60}")
    first, last = metrics_log[0], metrics_log[-1]
    print(f"时间跨度: {first['time']:.1f} → {last['time']:.1f}")
    print(f"总事件数: {last['events']}")
    print(f"最终 Gini: {last['gini']}")
    print(f"组织数: {last['n_orgs']}")
    print(f"总财富: {last['total_wealth']}")
    ginis = [s['gini'] for s in metrics_log]
    print(f"Gini 范围: [{min(ginis)}, {max(ginis)}]")
    print(f"Gini 非单调: {not all(ginis[i] <= ginis[i+1] for i in range(len(ginis)-1))}")
    print(f"局部价格方差: {last['price_var']}")
    # 验收检查
    print(f"\n--- 验收标准 ---")
    def mark(ok): return "PASS" if ok else "FAIL"
    print(f"[{mark(last['gini'] > 0.3)}] Gini > 0.3: {last['gini']}")
    mono = all(ginis[i] <= ginis[i+1] for i in range(len(ginis)-1))
    print(f"[{mark(not mono)}] Gini 非单调")
    print(f"[{mark(last['n_orgs'] > 0)}] 组织涌现: {last['n_orgs']} 个")
    has_mutation = any(s.get('mutation_count', 0) > 0 for s in metrics_log)
    print(f"[{mark(has_mutation)}] 制度突变发生")
    print(f"[{mark(last['price_var'] > 0.05)}] 局部价格差异: {last['price_var']}")
