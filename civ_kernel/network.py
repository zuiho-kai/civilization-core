from __future__ import annotations
import math
import random
from .models import World
from . import config


def generate_ws_graph(n: int, k: int, beta: float) -> dict[int, dict[int, float]]:
    """生成 Watts-Strogatz 小世界网络 + 距离衰减 trust 初始化。"""
    # Step 1: 环形格子
    adj: dict[int, set[int]] = {i: set() for i in range(n)}
    half_k = k // 2
    for i in range(n):
        for j in range(1, half_k + 1):
            neighbor = (i + j) % n
            adj[i].add(neighbor)
            adj[neighbor].add(i)

    # Step 2: 随机重连
    for i in range(n):
        for j in range(1, half_k + 1):
            if random.random() < beta:
                old = (i + j) % n
                if old in adj[i] and len(adj[i]) > 1:
                    candidates = [x for x in range(n) if x != i and x not in adj[i]]
                    if candidates:
                        new = random.choice(candidates)
                        adj[i].discard(old)
                        adj[old].discard(i)
                        adj[i].add(new)
                        adj[new].add(i)

    # Step 3: BFS 最短路径 + trust 赋值
    neighbors: dict[int, dict[int, float]] = {i: {} for i in range(n)}
    for i in range(n):
        # BFS 计算到所有直接邻居的距离
        for nb in adj[i]:
            dist = 1  # 直接邻居
            raw_trust = config.TRUST_BASE + config.TRUST_DECAY * math.exp(-dist)
            noise = random.gauss(0, config.TRUST_NOISE_STD)
            trust = max(config.TRUST_MIN, min(config.TRUST_MAX, raw_trust + noise))
            neighbors[i][nb] = trust
    return neighbors


def network_rewire(world: World, agent_id: int) -> None:
    """迁移时网络重连：旧连接衰减 + 新建二跳连接。"""
    agent = world.agents[agent_id]
    old_neighbors = list(agent.neighbors.keys())
    if not old_neighbors:
        return
    n_rewire = max(1, int(len(old_neighbors) * config.REWIRE_RATIO))
    to_rewire = random.sample(old_neighbors, min(n_rewire, len(old_neighbors)))

    for nb_id in to_rewire:
        agent.neighbors[nb_id] *= config.REWIRE_DECAY
        # 找二跳邻居
        nb = world.agents.get(nb_id)
        if nb:
            two_hop = [x for x in nb.neighbors if x != agent_id and x not in agent.neighbors]
            if two_hop:
                new_nb = random.choice(two_hop)
                agent.neighbors[new_nb] = config.INITIAL_REWIRE_TRUST
                world.agents[new_nb].neighbors[agent_id] = config.INITIAL_REWIRE_TRUST


def update_trust(world: World, a_id: int, b_id: int, delta: float) -> None:
    a, b = world.agents[a_id], world.agents[b_id]
    if b_id in a.neighbors:
        a.neighbors[b_id] = max(config.TRUST_MIN, min(config.TRUST_MAX, a.neighbors[b_id] + delta))
    if a_id in b.neighbors:
        b.neighbors[a_id] = max(config.TRUST_MIN, min(config.TRUST_MAX, b.neighbors[a_id] + delta))
