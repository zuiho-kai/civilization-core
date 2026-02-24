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
| 总代码规模 | ≤ 800 行 |
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
| `energy` | `float` | 可用行动能量（生产时锁定） |
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
| `rules` | `dict` | 当前制度参数集（税率、分配比例等） |
| `efficiency` | `float` | 内部协作效率（触发突变的指标之一） |
| `conflict_cost` | `float` | 累计冲突代价 |

注：Organization 是参数容器，不是预设制度模板。规则通过 `rule_mutation_event` 演化。

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

### 5.6 制度压力触发突变

制度变化不走投票流程，而是由结构压力驱动：

```python
if org.efficiency_drop > EFFICIENCY_THRESHOLD
   or migration_rate > MIGRATION_THRESHOLD
   or org.conflict_cost > CONFLICT_THRESHOLD:
       schedule Event(type='rule_mutation', target=org.id)

on rule_mutation:
    org.rules = mutate(org.rules)   # 随机扰动参数集
```

`rules` 是参数集（如税率 0.1 → 0.15），不是预设制度模板。
突变后 efficiency 和 conflict_cost 重新积累，允许多次迭代演化。

### 5.7 强制成本递增

强制行为的代价随施压方组织规模扩大而非线性增长，防止单一帝国收敛：

```
监督成本 = base_cost × (org_size ^ 1.5)
内部冲突概率 = 1 - e^(-α × org_size)
```

结果：
- 强制 + 扩张到一定规模后，维护成本超过收益
- 大型组织面临内部叛离风险，触发分裂或制度突变
- 系统自然维持多组织并存的动态平衡

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
ResourceLedger    → 全局守恒账本
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
| v0.1（当前） | 最小可运行内核，验证核心机制 | 事件引擎 + 三类原语 + 局部网络 |
| v0.2 | 组织涌现 + 制度突变 | OrgEngine + rule_mutation |
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
