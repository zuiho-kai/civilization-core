from __future__ import annotations
"""文明内核入口：初始化世界 -> 运行模拟 -> 输出统计。"""
import sys
import io
import random
import math

# Windows GBK 编码兼容
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith('gbk'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from .models import Agent, Event, World
from .engine import EventEngine
from .network import generate_ws_graph
from .agent_engine import (handle_wake_up, handle_produce_complete,
                           handle_exchange_request, handle_coerce_attempt)
from .org import handle_org_proposal, handle_rule_mutation, check_mutation_triggers
from .metrics import print_summary, snapshot
from . import config


def _random_simplex(n: int = 3) -> dict[str, float]:
    """随机生成 n 维 simplex 上的点（和为 1）。"""
    cuts = sorted(random.random() for _ in range(n - 1))
    vals = [cuts[0]] + [cuts[i] - cuts[i-1] for i in range(1, len(cuts))] + [1 - cuts[-1]]
    keys = ['gain', 'norm', 'trust']
    return {k: max(0.01, v) for k, v in zip(keys, vals)}


def initialize_world() -> World:
    world = World()
    # 生成网络
    graph = generate_ws_graph(config.NUM_AGENTS, config.WS_K, config.WS_BETA)
    # 创建 Agents
    for i in range(config.NUM_AGENTS):
        agent = Agent(
            id=i,
            wealth=config.INIT_WEALTH * random.uniform(0.5, 1.5),
            energy=config.INIT_ENERGY * random.uniform(0.8, 1.0),
            max_energy=config.MAX_ENERGY,
            regen_rate=config.REGEN_RATE * random.uniform(0.8, 1.2),
            neighbors=dict(graph[i]),
            disposition=_random_simplex(),
            learning_rate=random.uniform(0.01, 0.3),
            risk_aversion=random.uniform(0.0, 1.0),
            local_norm=0.5,
            activity_level=random.uniform(0.3, 1.0),
            perception_noise=random.uniform(0.1, 0.5),
        )
        world.agents[i] = agent
    return world


def run(seed: int | None = None) -> World:
    if seed is not None:
        random.seed(seed)
    world = initialize_world()
    engine = EventEngine(world)

    # 注册事件处理器
    engine.register('wake_up', handle_wake_up)
    engine.register('produce_complete', handle_produce_complete)
    engine.register('exchange_request', handle_exchange_request)
    engine.register('coerce_attempt', handle_coerce_attempt)
    engine.register('org_proposal', handle_org_proposal)
    engine.register('rule_mutation', handle_rule_mutation)

    # Bootstrap: 为每个 Agent schedule 初始 wake_up（随机偏移避免同时唤醒）
    for agent in world.agents.values():
        engine.schedule(Event(
            trigger_time=random.uniform(0.1, config.BASE_INTERVAL),
            type='wake_up',
            source_id=agent.id,
        ))

    # 注入 mutation 检查到 metrics 记录流程
    original_record = engine._record_metrics
    def _record_with_mutation():
        original_record()
        check_mutation_triggers(world)
    engine._record_metrics = _record_with_mutation

    # 运行
    print(f"启动文明内核：{config.NUM_AGENTS} 个 Agent，最大虚拟时间 {config.MAX_VIRTUAL_TIME}")
    engine.run()

    # 最终快照
    world.metrics_log.append(snapshot(world))
    print_summary(world.metrics_log)
    return world


def main():
    run(seed=42)


if __name__ == '__main__':
    main()
