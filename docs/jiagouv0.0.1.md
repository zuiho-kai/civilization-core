Continuous Agent Society Engine
高层原型设计图（战略 × 理论 × 架构）
0️⃣ 总体目标

构建一个：

实时运行

制度内生

非收敛

可扩展

无预设价值导向

的 Agent 社会操作系统。

1️⃣ 时间模型：连续时间 + 事件驱动
战略动机

我们拒绝回合制，是为了避免：

行为同步

群体共振

策略瞬间收敛

经济爆炸增长

我们要的是“持续扰动”。

理论来源

复杂系统非平衡理论（Ilya Prigogine）

Actor 并发模型（Erlang/OTP）

非平衡系统靠局部事件维持结构。

实际架构落点
┌───────────────────────┐
│      Global Clock     │
└─────────────┬─────────┘
              │
      ┌───────▼────────┐
      │   Event Queue   │  (min-heap)
      └───────┬────────┘
              │
      ┌───────▼────────┐
      │  Event Engine   │
      └─────────────────┘

工程决策：

使用优先队列

所有状态变更必须由 event 驱动

禁止周期性全局扫描

不这样做会发生什么？

500 Agent 同步行为

交易周期震荡

强制策略周期爆发

系统变成“节拍器”

2️⃣ 行为原语极简化（Produce / Exchange / Coerce）
战略动机

制度必须“涌现”，而不是“内置”。

如果允许 30 种复杂动作：

制度被编码

社会变脚本

Agent 只是执行器

我们只允许 3 种。

理论来源

生产关系结构分析（Karl Marx 的生产结构框架）

权力定义（Max Weber 对暴力垄断的定义）

不评价对错，只引用结构分析框架。

架构落点
class ActionType(Enum):
    PRODUCE
    EXCHANGE
    COERCE

所有复杂行为必须组合为这三种。

例如：

税收 = Coerce + Transfer

合同 = Exchange + Delayed Event

战争 = 连续 Coerce Event

不这样做的后果

制度预设

路径单一

收敛加速

3️⃣ 生产采用“时间占用模型”
战略动机

生产必须有机会成本。

否则：

所有人疯狂生产

强制永远不值得

经济爆炸

理论来源

时间结构生产理论（Eugen Bohm-Bawerk）

企业存在理论（Ronald Coase）

生产需要时间协同 → 组织出现。

架构落点
Agent.start_production()
  ↓
Lock Energy
Schedule Event (now + duration)
  ↓
OnComplete → ResourceCredit

无 tick 增长。

只有未来事件。

不这样做

无组织需求

无协作动力

无制度基础

4️⃣ 局部网络结构（无全局视野）
战略动机

全局信息会导致：

瞬时套利

完全竞争

价格统一

单一制度

我们需要制度并存。

理论来源

小世界网络理论（Duncan Watts）

社会资本理论（Pierre Bourdieu）

社会是局部网络，不是全局广播。

架构落点
Agent:
    neighbors: Dict[agent_id, trust_value]

事件传播只在局部扩散。

不这样做

全局价格统一

单一权力中心

制度消失

5️⃣ 组织自动生成（非创建）
战略动机

组织必须是结构结果。

不能是 UI 按钮。

理论来源

演化稳定策略（John Maynard Smith）

制度路径依赖（Douglass North）

重复互动 → 稳定结构。

架构落点
Cluster Detection Engine
   ↓
if density > threshold:
    spawn Organization Object

Organization = 一组参数容器。

不这样做

玩家操控制度

无结构涌现

社会退化成 UI 工具

6️⃣ 制度变化采用“压力触发突变”
战略动机

我们拒绝“民主投票模型”作为默认。

制度必须在压力下改变。

理论来源

政治秩序失序理论（Samuel Huntington）

复杂系统跃迁理论（Stuart Kauffman）

系统在扰动下跃迁。

架构落点
if org.efficiency_drop
   or migration_rate_high
   or conflict_cost_high:
       schedule rule_mutation_event

规则 = 参数集。

不这样做

制度线性优化

走向单一最优解

世界失去戏剧性

7️⃣ 扩展架构（500+ 承载）
战略目标

可持续运行

不 O(N²)

不全局扫描

架构结构
AgentRegistry
EventQueue (O log N)
NetworkGraph (sparse)
OrganizationIndex
ResourceLedger

约束：

平均网络度 < 20

事件局部化

禁止全局 recalculation

不这样做

性能崩溃

必须降规模

世界退回 50 Agent 小沙盒

8️⃣ 整体结构图（高层）
             ┌─────────────┐
             │  GlobalClock│
             └──────┬──────┘
                    │
            ┌───────▼────────┐
            │   Event Queue   │
            └───────┬────────┘
                    │
          ┌─────────▼─────────┐
          │    Event Engine    │
          └─────────┬─────────┘
                    │
 ┌──────────────┬───────────────┬──────────────┐
 │ Agent Engine │ Network Engine│ Org Engine   │
 └──────────────┴───────────────┴──────────────┘

这是可直接给工程拆分的模块。

9️⃣ 核心理念总结（给团队）

我们不是在做：

一个 AI 游戏。

我们在做：

一个制度生成服务器。

三大原则：

不设终局

不设道德

不设统一奖励

但：

必须设资源约束

必须设时间成本

必须设强制代价

否则世界塌缩。