# Continuous Agent Society Engine — 原型设计文档 v0.1

> 综合来源：`core.md`（愿景）· `designv0.0.1.md`（设计原理）· `jiagouv0.0.1.md`（架构落点）

---

## 1. 项目概述

### 1.1 项目定位

**Civilization Kernel（文明内核）** 是一个持续运行的虚拟社会引擎。由数百个自主 Agent 组成，通过极简行为规则，使生产关系、阶层分化、组织形成、制度演化等社会现象自然涌现。

**它不是：** 游戏、UI 应用、强化学习沙盒、脚本剧情系统。

**它是：** 一个纯模拟内核——实时事件驱动、制度内生演化、无预设终局的社会引擎。

与传统 AI 社会模拟的区别：

| 对比维度 | 传统强化学习模拟 | 本设计 |
|----------|-----------------|--------|
| 奖励函数 | 预设统一奖励 | 无统一奖励 |
| 更新方式 | 同步回合/tick | 异步事件驱动 |
| 制度来源 | 设计者写死 | 行为结构涌现 |
| 均衡状态 | 单一最优策略 | 多稳态并存 |
| 时间模型 | 离散 tick | 连续时间 |

### 1.2 v0.1 目标

实现最小可运行的文明内核，验证以下核心机制：

- 连续时间 + 事件队列驱动的主循环
- 三类行为原语（Produce / Exchange / Coerce）
- 生产时间占用模型（锁定资源 + 未来事件完成）
- 局部信任网络（无全局广播）
- Gini 系数度量财富分化
- 张力累积触发制度压力事件

### 1.3 约束条件

| 约束 | 规格 |
|------|------|
| 总代码规模 | ≤ 1200 行（含注释和空行；原 800 行在完整机制评估后上调） |
| 依赖 | 仅 Python 标准库 |
| LLM | 不接入 |
| 外部框架 | 不引入 |
| 并发 | 不使用多线程/async |
| 存储 | 不使用数据库 |

---

## 2. 核心设计原则

| 编号 | 原则 | 核心意图 | 若违反 |
|------|------|----------|--------|
| P1 | 连续时间 + 事件驱动 | 避免行为同步、群体共振、策略瞬间收敛 | 系统变成"节拍器"，500 Agent 同步震荡 |
| P2 | 极简行为原语 | 制度必须涌现，不能被预编码 | 制度被写死，Agent 退化为脚本执行器 |
| P3 | 生产具有时间成本 | 引入机会成本，形成协作需求 | 无组织需求，经济爆炸增长 |
| P4 | 局部网络结构 | 允许制度并存、文化分化、地区差异 | 全局价格统一，单一权力中心，制度消失 |
| P5 | 组织自动生成（非创建） | 组织是结构结果，不是玩家意志 | 社会退化为 UI 工具 |
| P6 | 制度压力触发突变 | 制度在失序下非线性演化，保持世界多样性 | 制度线性优化，走向单一最优解 |
| P7 | 强制成本递增 | 防止单一帝国收敛，保持动态平衡 | 强制永远最优，系统收敛 |
| P8 | 不定义"好制度" | 制度是适应结果，不是道德产物 | 演化被锁定，世界有终点 |
| P9 | Agent 是最小颗粒 | 所有结构从个体涌现，不允许预设国家/阶级 | 宏观结构被硬编码，失去涌现性 |

---

## 3. 系统架构

### 3.1 整体结构图

```
             ┌─────────────┐
             │ GlobalClock │
             └──────┬──────┘
                    │
            ┌───────▼────────┐
            │   EventQueue   │  (min-heap，按触发时间排序)
            └───────┬────────┘
                    │
          ┌─────────▼─────────┐
          │    EventEngine     │  (逐个 dispatch 事件)
          └─────────┬─────────┘
                    │
 ┌──────────────┬───┴────────────┬──────────────┐
 │ AgentEngine  │ NetworkEngine  │  OrgEngine   │
 │（行为原语）  │（信任传播）    │（组织检测）  │
 └──────────────┴───────────────┴──────────────┘
```

项目目录结构：

```
civ_kernel/
├── core/
│   ├── agent.py        # Agent 数据模型与行为原语
│   ├── world.py        # 世界状态 + EventEngine 主循环
│   ├── network.py      # 局部信任网络管理
│   ├── org.py          # 组织检测与生成
│   └── metrics.py      # Gini 系数、张力度量
└── main.py             # 入口，启动模拟
```

禁止添加：Web 框架、数据库、UI 文件、额外目录。

### 3.2 核心组件说明

| 组件 | 职责 |
|------|------|
| `GlobalClock` | 维护全局虚拟时间（浮点数），非 tick 计数器 |
| `EventQueue` | 优先队列（min-heap），按触发时间排序，所有状态变更必须由 event 驱动 |
| `EventEngine` | 循环 pop 最早事件并 dispatch 给对应 handler |
| `AgentEngine` | 接收事件后执行 Produce / Exchange / Coerce 原语 |
| `NetworkEngine` | 管理 Agent 局部 trust 网络，控制信息传播范围 |
| `OrgEngine` | 检测网络密度阈值，自动生成/解散 Organization 对象 |
| `ResourceLedger` | 资源守恒账本，防止凭空产生/消失 |

---

## 4. 数据模型

### 4.1 Agent

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int` | 唯一标识 |
| `wealth` | `float` | 当前财富值 |
| `energy` | `float` | 当前行动能量（生产时锁定，随时间自然回复） |
| `max_energy` | `float` | 能量上限，个体恒定 |
| `regen_rate` | `float` | 能量回复速率（每虚拟时间单位） |
| `neighbors` | `dict[int, float]` | 局部信任网络（agent_id → trust_value） |
| `status` | `float` | 阶层指数（财富 + 网络中心度计算） |
| `producing` | `bool` | 是否正在生产（锁定状态） |
| `org_id` | `int \| None` | 所属组织 ID（None = 无组织） |
| `disposition` | `dict[str, float]` | 行为倾向权重向量 `{gain, norm, trust}`，归一化，初始随机，可漂移 |
| `learning_rate` | `float` | 倾向漂移速率 η，每个 Agent 不同，初始随机 ∈ [0.01, 0.3] |
| `risk_aversion` | `float` | 风险厌恶系数 ∈ [0, 1]，影响 perceived_price_gap 计算 |
| `local_norm` | `float` | 本地近期成交成功率（EMA），仅 norm 权重高的 Agent 会重度使用 |
| `exchange_history` | `list[tuple]` | 近 N 次交易记录（对象、成交与否、Δwealth），用于 disposition 漂移 |
| `activity_level` | `float` | 行动活跃度 ∈ (0, 1]，影响 disposition 漂移贡献和 local_norm 更新权重 |

禁止添加：prompt 字段、LLM 字段、聊天内容、全局可见字段。

### 4.2 Organization

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int` | 唯一标识 |
| `members` | `set[int]` | 成员 agent_id 集合 |
| `rules` | `dict[str, float]` | 制度参数集（详见 5.5.1 枚举） |
| `treasury` | `float` | 公共池（税收积累） |
| `efficiency` | `float` | 内部协作效率（触发突变的指标之一） |
| `conflict_cost` | `float` | 累计冲突代价 |
| `legitimacy` | `float` | 组织合法性（v0.2 接入 LegitimacyMult） |

注：Organization 不是预设制度模板。rules 是连续数值空间中的一个点，通过 `rule_mutation_event` 随机游走演化。

### 4.3 Event

```python
@dataclass
class Event:
    trigger_time: float   # 触发虚拟时间
    type: str             # 事件类型
    source_id: int        # 发起 agent_id
    target_id: int | None # 目标 agent_id（可选）
    payload: dict         # 附加数据
```

常见事件类型：

| 事件类型 | 触发时机 |
|----------|----------|
| `produce_complete` | 生产周期结束，资源到账 |
| `exchange_request` | Agent 发起交换请求 |
| `coerce_attempt` | Agent 发起强制行为 |
| `rule_mutation` | 组织制度压力触发突变 |
| `org_spawn` | 网络密度阈值触发组织生成 |

### 4.4 World 全局状态

| 字段 | 类型 | 说明 |
|------|------|------|
| `agents` | `list[Agent]` | 所有 Agent |
| `orgs` | `dict[int, Organization]` | 所有组织 |
| `event_queue` | `list[Event]` | 优先队列 |
| `clock` | `float` | 当前虚拟时间 |
| `gini` | `float` | 当前 Gini 系数 |
| `tension` | `float` | 全局紧张度 |
| `resource_ledger` | `ResourceLedger` | 资源守恒账本 |

---

## 5. 核心机制

### 5.1 时间模型（连续时间 + 事件驱动）

世界基于连续时间运行，没有 tick，没有周期刷新，只有事件。

```
EventEngine 主循环：
while event_queue not empty:
    event = heappop(event_queue)       # 弹出最早事件
    clock = event.trigger_time         # 推进虚拟时间
    dispatch(event)                    # 执行对应 handler
```

工程约束：
- 使用 `heapq` 实现优先队列，复杂度 O(log N)
- 所有状态变更必须由 event 驱动，**禁止周期性全局扫描**
- 禁止任何形式的"全局 recalculation"

**世界启动（Bootstrap）**：`World.initialize()` 为每个 Agent 各 schedule 一个初始 `wake_up` 事件，触发时间加随机偏移（避免同时唤醒）。之后 Agent 完全自驱。

### 5.1.1 Agent 自决策机制（wake_up）

Agent 没有全局目标，只根据**局部状态**决策，行动后自行 schedule 下一次唤醒：

```
on wake_up(agent):
    if agent.energy < ENERGY_THRESHOLD:
        action = PRODUCE          # 能量不足，优先生产
    elif agent.wealth < avg_neighbor_wealth × 0.8:
        action = EXCHANGE         # 相对贫穷，尝试与最信任邻居交换
    elif 存在财富 < self × 0.5 的邻居 AND coerce_cost 可承受:
        action = COERCE           # 存在可强制对象，且代价值得
    else:
        action = PRODUCE          # 默认行为

    execute(action)

    # 行动后 schedule 下一次唤醒（富裕 Agent 更频繁）
    next_interval = BASE_INTERVAL / (1 + log(agent.wealth + 1))
    schedule wake_up(agent, now + next_interval)
```

关键性质：
- 决策只依赖 `agent.energy`、`agent.wealth`、`agent.neighbors`，**不读取全局状态**
- 富裕 Agent `next_interval` 更短 → 行动更频繁 → 马太效应自然涌现
- 没有"最优策略"，行为由当前状态驱动，允许多样化结果

### 5.2 行为原语（Produce / Exchange / Coerce）

所有 Agent 行为只能分解为三类：

```python
class ActionType(Enum):
    PRODUCE   # 生产：锁定能量 + 调度未来事件
    EXCHANGE  # 交换：双向资源转移（信任条件下）
    COERCE    # 强制：单向资源转移（需支付强制代价）
```

复杂社会行为的组合示例：

| 复杂行为 | 原语组合 |
|----------|----------|
| 税收 | Coerce + 资源 Transfer |
| 合同 | Exchange + Delayed Event |
| 战争 | 连续 Coerce Events |
| 联盟 | 多次 Exchange → trust 积累 |
| 国家 | Coerce 垄断 + 制度规则集 |

**禁止**预定义"国家""税收""战争"等高层对象，复杂结构必须从原语组合涌现。

### 5.2.1 Exchange 撮合机制

**全流程（事件驱动，无中央撮合，无全局市场）：**

```
Agent A wake_up → 决策 EXCHANGE
  ↓
① 对象选择（weighted random，非 deterministic）
   score(B) = α * trust(B)
            + β * perceived_price_gap(B)    # 见下方
            - γ * search_cost
   从 neighbors 中按 score 做加权随机抽样

② 估值计算（本地，不访问全局）
   A 生成 offer_price（基于自身稀缺度）
   schedule exchange_request(A→B)

③ B 收到请求，计算自身 valuation_B
   if offer_price 在 B 可接受区间内:
       → 接受，成交
   else:
       → counter_offer(price_B)
       if 交集存在: → 成交，价格随机取交集内一点（非固定中点）
       else:        → 拒绝，归类拒绝原因

④ 结算（如成交）
   ResourceLedger 记录双向转移
   trust 双向小幅提升
   双方 Δwealth → 驱动 disposition 漂移

⑤ 拒绝处理（分三层）
   price_gap 过大  → 更新对方估值模型，trust 不变
   多次低质量报价 → trust -= small_delta（恶意压价惩罚）
   已知违约历史   → trust -= larger_delta，加入黑名单
```

**防刷约束**：每次 wake_up 最多发起 `MAX_EXCHANGE_ATTEMPTS`（默认 2）次 exchange，每次消耗 energy，超限直接跳过。

**perceived_price_gap 计算（局部可观测，按 disposition 加权）：**

```python
gap_raw = abs(self.wealth - neighbor.wealth) / MAX_WEALTH

# gain 倾向高 → 直接用财富差（愣头青）
gap_gain = gap_raw

# norm 倾向高 → 财富差 × 本地成交风气（社会型）
gap_norm = self.local_norm * gap_raw

# trust 倾向高 → 信任够就忽略价格，不够直接拒绝（圈子型）
gap_trust = 0.0 if trust(neighbor) > TRIBE_THRESHOLD else -inf

# 加权混合
perceived_gap = (
    disposition['gain']  * gap_gain  +
    disposition['norm']  * gap_norm  +
    disposition['trust'] * gap_trust
) * (1 - self.risk_aversion)   # 风险厌恶压缩感知差距
```

### 5.2.2 Agent Disposition 模型

**连续权重向量，每个 Agent 独立，初始随机，终身可漂移：**

```python
# 初始化（每个 Agent 不同）
disposition = random_simplex_point()  # [gain, norm, trust]，sum = 1.0
learning_rate = uniform(0.01, 0.3)    # 固执 vs 见风使舵

# 每次 Exchange 完成后更新
outcome = Δwealth   # v0.1 信号：自身财富变化（极简，本地）

for dim in ['gain', 'norm', 'trust']:
    disposition[dim] += learning_rate * outcome * contribution[dim]

disposition = normalize(disposition)  # 保持 sum = 1.0
```

`contribution[dim]` = 做该决策时该维度的归一化权重（归因给影响最大的维度）。

**涌现效果预期：**

| 动态 | 机制 |
|------|------|
| 兄弟会形成 | `trust` 权重高的 Agent 聚集，互相强化 |
| 制度突变早期信号 | `norm` 权重高的 Agent 感知违约率上升，率先退出 |
| 马太效应加剧 | 富裕 Agent 强化现有倾向，行为趋于极端 |
| 地区风气分化 | 不同子网中 `local_norm` 独立演化 |

**v0.2 可扩展：** outcome 信号升级为 `Δwealth - avg_neighbor_Δwealth`（相对收益）。

### 5.2.3 行为修正因子

四个修正因子叠加在决策和学习过程上，增加个体差异和网络层次感：

**① 风险感知（risk_aversion）**

同一个 perceived_price_gap，不同 Agent 对风险的敏感度不同；谨慎型 Agent 宁愿错过好机会也不想被 Coerce。

```python
perceived_gap *= (1 - risk_aversion)   # risk_aversion ∈ [0, 1]
```

效果：提高系统对极端财富差的鲁棒性，防止所有 Agent 一窝蜂涌向高差价交易。

**② 交易频率 / 活跃度（activity_level）**

现实中有些 Agent 很活跃，有些低调。频率高的 Agent 对 norm 的反馈更快，也更容易成为制度催化剂。

```python
contribution = disposition * activity_level
```

用于 `local_norm` 更新和 trust 变化计算的加权。高活跃 Agent 的每次行为对局部网络影响更大，自然形成"意见领袖"效应，增加局部网络差异性。

**③ 历史波动 / 信号噪声（EMA 平滑 local_norm）**

社会型 Agent（`norm` 权重高）根据近期趋势而非单次事件调整 disposition，模拟群体学习延迟：

```python
local_norm = EMA(recent_trade_success, alpha=0.3)
```

`alpha` 越小，记忆越长，对短期噪声越不敏感。效果：避免 norm 过度敏感导致过快收敛或群体恐慌。

**④ 社会距离（social_distance）**

即便在局部网络内，也有亲疏关系。trust 的有效值根据邻居的网络跳数衰减：

```python
effective_trust = trust / (1 + social_distance)
```

`social_distance` = 两个 Agent 之间的最短路径跳数（直接邻居 = 0，邻居的邻居 = 1，以此类推）。效果：自然产生圈子层次，`trust` 倾向高的 Agent 形成紧密部落，外层信任衰减明显。

**四因子协同涌现预期：**

| 组合 | 涌现效果 |
|------|----------|
| 高 activity + 高 norm | 制度催化剂：快速传播交易规范，带动局部风气 |
| 高 risk_aversion + 低 activity | 保守隐士：几乎不交易，财富缓慢增长，抗 Coerce |
| 低 social_distance + 高 trust | 核心圈子：高效内部交换，排斥外部 Agent |
| 高 activity + 低 risk_aversion | 投机者：频繁高风险交易，财富波动大，容易暴富或破产 |

### 5.3 生产时间占用模型

生产不是瞬时收益，而是占用时间、锁定资源、未来事件完成：

```
Agent.start_production():
  → 锁定 energy（producing = True）
  → schedule Event(trigger_time = now + duration, type='produce_complete')

on produce_complete:
  → 释放 energy（producing = False）
  → 资源记入 ResourceLedger（守恒）
```

**禁止**任何"每帧增长"或"瞬时资源获取"逻辑。

生产 duration 受以下因素影响：
- Agent 自身 energy 水平
- 所属组织的协作加成（org 内协作可缩短 duration）

**energy 回复机制：** 每次 `wake_up` 或 `produce_complete` 时，根据距上次事件的时间差回复 energy：

```python
elapsed = now - agent.last_event_time
agent.energy = min(agent.max_energy, agent.energy + agent.regen_rate * elapsed)
```

energy 不可转移所有权、不可永久剥夺。Coerce 不抢 energy，只控制 wealth 产出方向（制度层控制）。

### 5.3.1 ResourceLedger 与资源模型

**核心原则：守恒的是因果，不是总量。**

系统区分两类资源：

| 资源 | 类型 | 是否守恒 | 语义 |
|------|------|----------|------|
| `energy` | Flow（流量） | 不守恒 — 个体可再生，有上限 | 行动能力 / 劳动力 / 时间 |
| `wealth` | Stock（存量） | 不守恒 — 可通过生产增长 | 可积累价值 / 产出 |

**"因果守恒"定义：** 所有 wealth/energy 变更必须来自合法事件，禁止非事件写入。

合法事件类型：

| 事件 | wealth 变化 | energy 变化 |
|------|-------------|-------------|
| `produce_complete` | +（energy → wealth 转化） | 释放锁定量，自然回复 |
| `exchange_settle` | A↔B 双向转移，总和为零 | 每次 exchange 消耗少量 energy |
| `coerce_transfer` | B→A 单向转移，总和为零 | A 消耗自身 energy（强制是累活） |
| `energy_regen` | 无 | +（自然回复，≤ max_energy） |

**禁止：** 任意修改余额、非事件写入、跨 Agent energy 转移。

**wealth 通胀约束（v0.1）：** 不引入折旧机制，靠以下自然约束限制增长率：
- 生产需要消耗 energy → energy 有上限且回复有速率
- 生产需要时间（duration）→ Agent 不能同时生产两份
- 生产函数：`wealth_output = energy_spent × PRODUCTION_EFFICIENCY × coordination_factor`

**ResourceLedger 职责：**

```python
class ResourceLedger:
    def transfer_wealth(self, from_id, to_id, amount):
        # 断言：amount > 0，from 余额充足
        # 扣减 → 增加，原子操作

    def produce(self, agent_id, energy_cost):
        # wealth_gain = energy_cost * PRODUCTION_EFFICIENCY
        # agent.energy -= energy_cost（已在 start_production 时锁定）
        # agent.wealth += wealth_gain

    def audit_event(self, event, before_snapshot, after_snapshot):
        # 校验该 event 前后的 wealth/energy 变化是否合法
        # 不合法则 raise（开发期断言，非运行时容错）
```

**设计理由：**
- energy 个体可再生 → 系统不会冻结（开放能量系统，参考 Prigogine 耗散结构理论）
- energy 不可转移 → 物理层防止"剥夺行动能力"导致吸收态
- wealth 可增长 → 生产有意义，经济增长存在
- 制度层（Coerce + org.rules）控制产出分配 → 奴役/税收/掠夺通过 wealth 流向实现，不需要物理层支持

### 5.4 局部网络结构

每个 Agent 只维护局部 trust 网络，信息不全局传播：

```python
Agent.neighbors: dict[agent_id, trust_value]
```

规则：
- 初始网络为随机稀疏图，平均度 < 20
- Exchange 成功 → trust 小幅提升
- Coerce 成功（对方视角）→ trust 大幅下降
- 信息/事件只在 trust > threshold 的直接邻居间传播
- **社会距离衰减**：`effective_trust = trust / (1 + social_distance)`，直接邻居 distance=0（全额 trust），二跳邻居 distance=1（trust 减半），以此类推。Agent 只能感知 ≤2 跳范围内的邻居信息
- **禁止**全局广播、全局价格查询、全局状态感知

### 5.5 组织自动生成

组织不可手动创建，必须从网络结构涌现：

```
OrgEngine（周期性局部扫描，非全局）:
  对每个连通子图计算密度和交互频率
  if density > DENSITY_THRESHOLD
     and exchange_frequency > FREQ_THRESHOLD:
       spawn Organization(members=subgraph_nodes)
```

生成的 Organization：
- 初始 rules 为默认参数集（低税率、平均分配）
- 成员可通过 Exchange 加强内部 trust，进而影响 efficiency
- 当 efficiency 下降或 conflict_cost 过高时，触发 `rule_mutation_event`

组织解散条件：成员数低于 `MIN_ORG_SIZE`（默认 3）。

### 5.5.1 Organization.rules 枚举

rules 是 `dict[str, float]`，分为 6 类。每个 key 都直接影响 Agent 收益函数（不影响收益的 rule 不该存在）。

**① 经济规则（v0.1 实现）**

| key | 范围 | 默认 | 含义 | 对 Agent 的影响 |
|-----|------|------|------|----------------|
| `tax_rate` | [0, 0.5] | 0.05 | 成员 Exchange 收益抽成比例 | `net_income = production × (1 - tax_rate) + redistribution_share` |
| `redistribution_ratio` | [0, 1] | 0.5 | 税收再分配方式：0=全给领导，1=均分全员 | 影响组织内贫富差距和成员留存意愿 |
| `public_goods_efficiency` | [0, 1] | 0.3 | 税收转化为生产力加成的效率 | `productivity_bonus = public_goods_efficiency × log(org_size)` |

**② 强制规则（v0.1 实现）**

| key | 范围 | 默认 | 含义 | 对 Agent 的影响 |
|-----|------|------|------|----------------|
| `internal_coercion_tolerance` | [0, 1] | 0.2 | 对内部 Coerce 的容忍度 | 低容忍 → 内部 Coerce 额外 trust 惩罚 ×2；高容忍 → 军事化组织 |
| `punishment_severity` | [0, 1] | 0.3 | 违规/叛逃惩罚力度 | `C_coercion = internal_conflict_prob × punishment_severity × wealth` |
| `enforcement_cost_share` | [0, 1] | 0.5 | 组织补贴个体强制成本的比例 | 0=个人全扛，1=org 公共池出钱 |

**③ 权力分配规则（v0.1 简化实现，v0.2 完整）**

| key | 范围 | 默认 | 含义 | 对 Agent 的影响 |
|-----|------|------|------|----------------|
| `delegation_rate` | [0, 1] | 0.5 | 成员 power 多少可被组织调用 | 高 → 中央 effective power 强；低 → 分封/虚君 |

v0.2 扩展：`decision_mode`（autocracy/council/vote）、`decision_cost_factor`。

**④ 意识形态规则（v0.2 实现，v0.1 默认中性）**

| key | 范围 | 默认 | 含义 | 对 Agent 的影响 |
|-----|------|------|------|----------------|
| `ideology_strength` | [0, 1] | 0.0 | 意识形态凝聚力 | 提升 legitimacy，但 extremity 高时压低 productivity |
| `ideology_extremity` | [0, 1] | 0.0 | 意识形态极端程度 | `productivity_penalty = ideology_extremity × base_penalty` |

**⑤ 成员流动规则（v0.1 实现）**

| key | 范围 | 默认 | 含义 | 对 Agent 的影响 |
|-----|------|------|------|----------------|
| `entry_barrier` | [0, 1] | 0.3 | 加入所需最低 avg trust（对现有成员） | 高 → 排外封闭圈子；低 → 开放商贸联盟 |
| `exit_penalty` | [0, 1] | 0.1 | 退出时的 wealth 罚没比例 | 高 → 极权锁定；低 → 自由流动 |

**⑥ 对外姿态规则（v0.1 实现）**

| key | 范围 | 默认 | 含义 | 对 Agent 的影响 |
|-----|------|------|------|----------------|
| `external_aggression_bias` | [0, 1] | 0.3 | 对外 Coerce 的倾向性 | 影响成员 wake_up 时 Coerce 决策权重 |
| `loot_policy` | [0, 1] | 0.3 | 组织层面的掠夺比例上限 | 覆盖个体 LOOT_RATIO，`effective_loot = min(LOOT_RATIO, loot_policy)` |

**制度类型 × rules 参数对照：**

| 制度 | tax | redist | public_goods | delegation | exit_pen | aggression | loot_pol |
|------|-----|--------|--------------|------------|----------|------------|----------|
| 游牧联盟 | 低 | 高 | 低 | 高 | 低 | 高 | 高 |
| 农业帝国 | 中高 | 中 | 高 | 高 | 中 | 中 | 低 |
| 商贸共和 | 中 | 中 | 高 | 低 | 低 | 低 | 低 |
| 极权国家 | 高 | 低 | 中 | 高 | 高 | 高 | 中 |
| 封建分权 | 低 | 低 | 低 | 低 | 中 | 中 | 中 |

### 5.5.2 Agent 加入/退出组织决策

Agent 加入组织是收益驱动的，不是指令驱动的：

```
EV_join(A, O) =
    E_economic + E_security + E_power
  - C_tax - C_coercion - C_exit_lock

EV_outside(A) =
    production - external_coerce_risk × wealth

Agent 加入条件：EV_join - EV_outside > JOIN_THRESHOLD
Agent 退出条件：EV_outside - EV_join > EXIT_THRESHOLD（需另付 exit_penalty）
```

**各项定义：**

```python
# 经济收益：税后收入 + 再分配 + 公共品
E_economic = (1 - tax_rate) * production
           + treasury * redistribution_ratio / org_size
           + public_goods_efficiency * log(org_size) * production

# 安全收益：组织提供保护，降低被外部 Coerce 的风险
E_security = (coerce_risk_outside - coerce_risk_inside) * wealth
# coerce_risk_inside = coerce_risk_outside × (1 - org_protection_power)

# 权力收益（v0.1 简化）
E_power = delegation_rate * treasury / org_size

# 税收成本
C_tax = tax_rate * production

# 内部强制风险
C_coercion = internal_conflict_prob * punishment_severity * wealth

# 退出锁定成本（影响加入意愿——加入前就知道退出要罚钱）
C_exit_lock = exit_penalty * wealth * EXIT_PROBABILITY_ESTIMATE
```

**EV_coerce 嵌入决策空间（掠夺 vs 生产的自动切换）：**

```python
# Agent 每次 wake_up 的行为选择变为收益比较：
EV_produce = energy_spent * PRODUCTION_EFFICIENCY * (1 - tax_rate_if_in_org)
EV_coerce  = p_success * loot_amount - energy_cost - wealth_cost - trust_penalty
EV_exchange = expected_trade_surplus * (1 - tax_rate_if_in_org)

# loot_amount 三重上限：
loot_amount = min(
    loot_ratio * B.wealth,          # 对方承受上限
    carry_capacity(A),               # 搬运能力（v0.2: ∝ energy × mobility）
    destruction_limit                 # 防止完全清零（v0.2）
)

# 当 EV_coerce > EV_produce 时，社会自然转入掠夺倾向
# 当 EV_produce > EV_coerce 时，社会自然转入生产主导
# 不需要手动切换"模式"
```

### 5.6 制度压力触发突变

制度变化不走投票流程，而是由结构压力驱动：

```python
if org.efficiency_drop > EFFICIENCY_THRESHOLD
   or migration_rate > MIGRATION_THRESHOLD
   or org.conflict_cost > CONFLICT_THRESHOLD:
       schedule Event(type='rule_mutation', target=org.id)
```

**突变机制（具体化）：**

```python
# 可突变的 key（不是所有 rule 都突变）
MUTATABLE_KEYS = [
    'tax_rate', 'redistribution_ratio', 'delegation_rate',
    'external_aggression_bias', 'loot_policy',
    'entry_barrier', 'exit_penalty'
]
# ideology_strength 和 public_goods_efficiency 不参与随机突变
# （前者需要意识形态事件驱动，后者需要技术事件驱动）

MUTATION_STEP = 0.05  # 每次扰动幅度

on rule_mutation:
    for key in MUTATABLE_KEYS:
        org.rules[key] += normal(0, MUTATION_STEP)
        org.rules[key] = clamp(org.rules[key], MIN[key], MAX[key])
```

**突变阈值默认值：**

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `EFFICIENCY_THRESHOLD` | 0.3 | efficiency 下降超过 30% 触发 |
| `MIGRATION_THRESHOLD` | 0.2 | 单周期内 20% 成员退出触发 |
| `CONFLICT_THRESHOLD` | 成员 avg_wealth × 0.5 | 累计冲突代价过高触发 |

突变后 efficiency 和 conflict_cost 重新积累，允许多次迭代演化。

### 5.7 Coerce 行为机制

#### 5.7.1 EffectivePower 框架

Power 采用模块化乘法结构，v0.1 实现前两个模块，其余预留接口默认 1.0：

```
EffectivePower = BaseCapacity × OrgMultiplier × LegitimacyMult × IdeologyMod × ContextMod
```

**① BaseCapacity（个体基础能力）— v0.1 实现**

```python
BaseCapacity = a1 * energy + a2 * wealth
# v0.2+ 扩展位：+ a3 * physique + a4 * tech_level
```

**② OrganizationMultiplier（规模放大 + 治理成本）— v0.1 实现**

```python
OrgMultiplier = (1 + b1 * log(org_size + 1)) / (1 + b2 * org_size)
# org_size = 1 for 无组织 Agent → multiplier ≈ 1.0
```

结构特性（"规模双刃剑"）：
- log 提供规模收益（递减）
- 分母提供治理成本（递增）
- 中型组织 power 峰值最大，超大组织开始衰退
- 支持：国家崛起 → 鼎盛 → 崩溃的完整周期

**③ LegitimacyMultiplier — v0.2 实现，v0.1 默认 1.0**

```python
LegitimacyMult = 1 + c1 * legitimacy   # legitimacy 来源：trust 网络、loyalty、程序合法性
```

支持场景：苏联式信任崩溃（legitimacy 骤降 → effective power 下降，即使 org_size 不变）、周天子式名存实亡（legitimacy > 0 但 enforcement ≈ 0）、共和国（legitimacy 来自程序一致性）。

**④ IdeologyModifier — v0.3 实现，v0.1 默认 1.0**

```python
IdeologyMod = 1 + f1 * ideology_cohesion - f2 * ideology_extremity
```

温和意识形态 → 稳定加成；极端意识形态 → 短期增强但长期衰退（生产效率下降）。
支持场景：纳粹式高速动员→扩张→崩溃、红色高棉式意识形态压制经济理性。

**⑤ ContextModifier — v0.3 实现，v0.1 默认 1.0**

```python
ContextMod = 1 + d1 * terrain_bonus - d2 * instability
```

**v0.1 默认参数（待校准）：**

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `a1` | 1.0 | energy 对 power 的权重 |
| `a2` | 0.5 | wealth 对 power 的权重 |
| `b1` | 1.0 | 组织规模放大系数 |
| `b2` | 0.05 | 治理成本系数（决定最优组织规模拐点） |

**扩展路线（BaseCapacity 未来可插入）：**

| 扩展变量 | 语义 | 版本 |
|----------|------|------|
| `physique` | 体质（战斗/生产/精神型） | v0.2+ |
| `tech_level` | 技术水平 | v0.2+ |
| `sovereignty` | 子组织主权度 | v0.3+（支持唐朝式藩镇割据） |
| `delegation_rate` | 授权率 | v0.3+（支持选帝侯式结构） |

**支持的制度涌现类型（完整框架下）：**

| 制度类型 | 关键驱动变量 | 历史参照 |
|----------|-------------|----------|
| 帝国集中型 | 高 OrgMultiplier | 唐帝国 |
| 联邦崩溃型 | LegitimacyMult 骤降 | 苏联 |
| 分封象征型 | 高 legitimacy + 低 enforcement | 周天子 |
| 选举皇帝型 | delegation 结构 | 神圣罗马帝国 |
| 商业寡头共和 | 高 a2（wealth 权重） | 威尼斯共和国 |
| 军阀碎片化 | 高 a1 + 中 OrgMult | 战国 / 战国时代（日本） |
| 极权动员型 | 高 IdeologyMod | 纳粹德国 |
| 革命清洗型 | 极端 ideology_extremity | 红色高棉 |
| 掠夺流动型 | 高 mobility + 低 local_dependency | 维京时代 / 蒙古帝国 |
| 农民起义席卷型 | legitimacy 崩溃 + 高 inequality + 高 destruction | 闯王（李自成） |
| 可控常态战争 | 中 loot + 高 local_dependency + 制度化 | 百年战争 / 中世纪欧洲 |
| 游牧掠夺—定居转型 | 高 mobility → 逐渐提高 local_dependency | 蒙古→元朝 |
| 技术官僚型 | 高 tech_level + 高 coerce 成本 | 新加坡 |
| 无国家商贸网络 | 高 trust + 低 coerce 收益 | 汉萨同盟 |

#### 5.7.2 Coerce 完整流程

```
Agent A wake_up → 决策 COERCE（目标 B）
  ↓
① 前置检查
   - A.wealth > coerce_wealth_cost（付不起就放弃）
   - A.energy > coerce_energy_cost
   - B 在 A 的 neighbors 中（只能强制认识的人）

② 代价计算（双重消耗）
   energy_cost = BASE_COERCE_ENERGY                    # 行动成本（体力）
   wealth_cost = BASE_COERCE_WEALTH × (1 + org_cost)   # 工具/组织成本
   org_cost = (org_size ^ 1.5) / COERCE_SCALE_FACTOR   # 组织越大维护越贵
   代价由发起 Agent 本人承担（org 可通过 rules 补贴，但必须记账到个体）

③ 成功概率（对称比例函数）
   power_A = EffectivePower(A)
   power_B = EffectivePower(B)
   p_success = power_A / (power_A + power_B)

④ 结算
   if 成功:
       loot = min(B.wealth × LOOT_RATIO, energy_spent × LOOT_EFFICIENCY)
       B.wealth -= loot
       A.wealth += loot - wealth_cost
       trust(B→A) → 接近 0
       B 的邻居：trust(→A) 小幅下降（局部声誉惩罚）
   if 失败:
       A.wealth -= wealth_cost（白付）
       A.energy -= energy_cost（白付）
       额外失败惩罚 [待定：见下方待决策项]
       trust(B→A) 大幅下降

⑤ 后续影响
   成功：A 短期获利，但局部 trust 受损 → 未来 Exchange 机会减少
   失败：A 纯亏损 → 抑制盲目强制
```

#### 5.7.3 强制成本递增（组织规模）

```python
监督成本 = base_cost × (org_size ^ 1.5)
内部冲突概率 = 1 - e^(-α × org_size)
```

| 组织规模 | 监督成本倍数 | 内部冲突概率（α=0.05） |
|----------|-------------|----------------------|
| 5 人 | ×11 | 22% |
| 10 人 | ×32 | 39% |
| 20 人 | ×89 | 63% |
| 50 人 | ×354 | 92% |

#### 5.7.4 LOOT_RATIO 与掠夺可持续性

**核心设计理由：** LOOT_RATIO 不应是固定小数，而是 ∈ [0, 1] 的宽范围。关键不在于"拿多少"，而在于"掠夺是否可持续"——同样 70% 的掠夺，农业社会会自毁，游牧社会可存活。

**v0.1 实现：** LOOT_RATIO 为全局默认参数，默认 0.3。v0.2 引入掠夺可持续性框架后可上调范围。

**v0.2+ 掠夺可持续性框架（完整设计，v0.1 不实现）：**

掠夺的长期后果取决于三个因子：

```python
# ① destruction_factor — 掠夺造成的生产力破坏
destruction = loot_ratio ** 2 × violence_intensity
# 掠夺越狠破坏越大，但关系是平方（少量掠夺破坏极小，大量掠夺破坏骤增）

# ② mobility — 掠夺方的机动能力
# 高 mobility → 掠夺后可撤离，不承担破坏后果
# 低 mobility → 掠夺自己的邻居 = 破坏自己的生产环境

# ③ local_dependency — 被掠夺方对本地生产的依赖度
# 农业社会 local_dependency 高 → 被掠夺后恢复慢
# 商贸社会 local_dependency 中 → 有替代供应链
# 游牧社会 local_dependency 低 → 掠夺对其影响小

future_productivity_loss = destruction × local_dependency × (1 - mobility)
```

**三种掠夺模式对照：**

| 类型 | 历史参照 | loot_ratio | mobility | local_dep | destruction | 可持续？ |
|------|----------|------------|----------|-----------|-------------|----------|
| 农民起义席卷 | 闯王（李自成） | 高（0.7+） | 低 | 高 | 极高 | 不可持续 — 摧毁生产基础后自身也崩溃 |
| 游牧/海盗掠夺 | 维京 / 蒙古 | 高（0.6+） | 高 | 低 | 中 | 可持续 — 掠夺后撤离，不依赖本地 |
| 中世纪常态战争 | 百年战争 | 低中（0.2） | 中 | 中高 | 低 | 可持续 — 战后生产恢复，制度化战争 |
| 掠夺→定居转型 | 蒙古→元朝 | 高→低 | 高→低 | 低→高 | 高→低 | 转型期 — mobility 下降后必须转生产 |

**为什么这能自然涌现：** Agent 不需要被标记为"游牧"或"农业"。只要 mobility 和 local_dependency 作为 Agent 属性存在，不同组合的 Agent 群体会自然形成不同的经济模式。高 mobility + 低 local_dependency 的 Agent 聚集 → 游牧掠夺联盟自然涌现。

**覆盖性验证 — 清朝模式（Qing dynasty 全生命周期）：**

清朝不是单一制度，而是一条完整的生命周期轨迹。验证当前框架能否覆盖其每个阶段：

| 阶段 | 历史特征 | 框架中的对应机制 | 是否已覆盖 |
|------|----------|-----------------|-----------|
| 入关前（后金） | 草原军事集团，高机动掠夺 | 高 mobility + 低 local_dependency → 游牧掠夺模式 | ✅ 已有 |
| 入关整合 | 军事集团接管农业财政，八旗+绿营并存 | mobility/local_dependency 属性漂移（高→低），不需要模式切换机制 | ✅ 属性漂移 |
| 康乾盛世 | 规模扩张、生产力强、合法性高 | OrgMultiplier 接近峰值 + LegitimacyMult 高 | ✅ 已有 |
| 晚期衰退 | 人口压力、财政刚性、治理成本过高 | `(1+log(org_size)) / (1+b2*org_size)` 分母主导 → 规模成本超过收益 | ✅ 已有 |
| 外部冲击（鸦片战争） | 技术差距导致军事失衡 | tech_level 在 BaseCapacity 扩展位，v0.2+ 接入 | ⏳ v0.2 |
| 内部起义（太平天国） | legitimacy 崩溃 + inequality 高 | 农民起义席卷模式（高 destruction + 低 mobility） | ✅ 已有 |

关键结论：清朝模式的核心动力学（游牧→帝国→衰退→崩溃）不需要新增机制，靠已有变量的连续漂移即可覆盖。唯一缺口是"外部文明技术差距"（tech_level），已规划在 v0.2 的 BaseCapacity 扩展位中。

#### 5.7.5 待决策项

以下参数在设计讨论中尚未拍板，编码前必须确认：

| 参数 | 含义 | 候选值 | 状态 |
|------|------|--------|------|
| `失败额外惩罚` | 强制失败时除白付成本外的额外损失 | 无 / 固定50%投入 / f(power_B/power_A) | **待定** |

**验证指标（运行时校准）：** 长期强制行为占比应 < 60%，若高于此值说明强制收益过高，需降低 LOOT_RATIO 或提高失败惩罚。

---

## 6. 扩展架构约束（500+ Agent）

v0.1 目标 50–200 Agent，但架构设计必须保证可扩展至 500+：

| 组件 | 约束 |
|------|------|
| EventQueue | O(log N) 优先队列，禁止 O(N) 全扫描 |
| NetworkGraph | 稀疏图，平均度 < 20，禁止全连接 |
| OrgEngine | 局部子图检测，不遍历全体 Agent |
| AgentEngine | 无全局锁，事件局部化 |

关键数据结构：

```
AgentRegistry     → dict[id, Agent]
EventQueue        → heapq（min-heap by trigger_time）
NetworkGraph      → 稀疏邻接表
OrganizationIndex → dict[id, Organization]
ResourceLedger    → 因果守恒账本（事件来源合法性审计）
```

---

## 7. v0.1 验收标准

运行足够时间后，必须观察到以下现象：

- [ ] **财富分层**：Agent 间出现明显贫富差距，Gini > 0.3
- [ ] **Gini 非单调**：Gini 系数随时间波动，不单调增长或收敛
- [ ] **制度压力事件**：至少发生一次 `rule_mutation_event`
- [ ] **组织涌现**：至少自动生成一个 Organization（非手动创建）
- [ ] **强制有代价**：Coerce 行为不是永远最优策略，存在反制
- [ ] **局部价格差异**：不同网络区域的交换比率出现分化

若无上述现象，优先检查：参数阈值是否过松/过紧，而非修改机制。

---

## 8. 禁止事项

| 类别 | 禁止项 |
|------|--------|
| 时间模型 | 任何形式的 tick 循环、定时全局扫描 |
| 行为 | 预定义税收/战争/国家等高层对象 |
| 信息 | 全局广播、Agent 感知全局状态 |
| 组织 | 手动创建组织（UI 按钮、代码直接 spawn） |
| 制度 | 投票机制、预设进步方向、道德评判 |
| 生产 | 瞬时资源增长、每帧/每 tick 自动增加 |
| 技术 | LLM API、数据库、Web 框架、多线程/async |
| 结构 | 预设国家/阶级模板，Agent 血统特权 |

---

## 9. 演进路线

| 阶段 | 目标 | 关键新增 |
|------|------|----------|
| v0.1（当前） | 最小可运行内核，验证核心机制 | 事件引擎 + 三类原语 + 局部网络 + Power(Base+Org) |
| v0.2 | 组织涌现 + 制度突变 + 信任驱动 | OrgEngine + rule_mutation + LegitimacyMult + physique/tech_level |
| v0.3 | 制度多样性 | IdeologyMod + ContextMod + sovereignty/delegation（支持分封/联邦/极权） |
| 第二阶段 | 500+ Agent 持续稳定运行 | 性能优化、局部化调度 |
| 第三阶段 | 外部 Agent 接入 | 开放 API 接口、虚拟劳动力市场 |
| 最终目标 | 持续运行的制度实验场 | 无终局、无预设价值导向 |

---

## 10. 理论来源索引

| 设计决策 | 理论来源 | 核心观点 |
|----------|----------|----------|
| 连续时间 + 事件驱动 | Ilya Prigogine（耗散结构理论） | 非平衡系统通过局部事件维持结构 |
| 连续时间 + 事件驱动 | Erlang/OTP Actor 模型 | 消息驱动并发，减少全局同步锁 |
| 三类行为原语 | Karl Marx（生产结构分析框架） | 生产方式决定制度形态 |
| 三类行为原语 | Max Weber（国家暴力垄断定义） | 强制权力的结构性分析 |
| 生产时间占用 | Eugen Böhm-Bawerk（时间结构生产） | 生产具有延迟，引入机会成本 |
| 生产时间占用 | Ronald Coase（交易成本理论） | 组织降低协作交易成本 |
| 局部网络结构 | Duncan Watts（小世界网络理论） | 真实社会由局部连接构成 |
| 局部网络结构 | Pierre Bourdieu（社会资本理论） | 社会关系本身是资本 |
| 组织自动生成 | John Maynard Smith（演化稳定策略） | 稳定策略在重复互动中形成 |
| 组织自动生成 | Douglass North（制度经济学） | 制度源于重复交易的路径依赖 |
| 制度压力突变 | Samuel Huntington（政治秩序失序） | 制度变迁常源于失序而非理性设计 |
| 制度压力突变 | Stuart Kauffman（复杂适应系统） | 系统在扰动下跃迁至新稳态 |
| 强制成本递增 | Paul Kennedy（帝国过度扩张） | 规模扩张超过临界点导致崩溃 |
| 强制成本递增 | James Buchanan（公共选择理论） | 大规模集体决策效率递减 |
| 不定义好制度 | Max Weber（价值中立社会科学） | 科学分析不预设价值判断 |
