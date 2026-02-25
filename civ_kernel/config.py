from __future__ import annotations
# 全局常量与默认参数
# 所有可调参数集中管理，禁止在其他模块硬编码数字

# --- 世界参数 ---
NUM_AGENTS = 100
MAX_VIRTUAL_TIME = 1000.0
METRICS_INTERVAL = 50  # 每 N 个事件记录一次指标

# --- 网络参数 ---
WS_K = 10           # Watts-Strogatz 每侧邻居数（平均度 = K）
WS_BETA = 0.15      # 重连概率
TRUST_BASE = 0.4    # 初始 trust 基础值
TRUST_DECAY = 0.4   # 距离衰减系数
TRUST_NOISE_STD = 0.05
TRUST_MIN = 0.05
TRUST_MAX = 0.95

# --- Agent 参数 ---
INIT_WEALTH = 10.0
INIT_ENERGY = 1.0
MAX_ENERGY = 1.0
REGEN_RATE = 0.1     # energy 每虚拟时间单位回复
BASE_INTERVAL = 5.0  # wake_up 基础间隔
ENERGY_THRESHOLD = 0.3
WEALTH_COMPARE_RATIO = 0.8   # 相对贫穷判断
COERCE_WEALTH_RATIO = 0.5    # 存在可强制对象的判断

# --- 生产参数 ---
PRODUCTION_EFFICIENCY = 1.0
PRODUCTION_DURATION_BASE = 3.0   # 基础生产时间
PRODUCTION_ENERGY_COST = 0.5     # 每次生产消耗的 energy

# --- 交换参数 ---
MAX_EXCHANGE_ATTEMPTS = 2
EXCHANGE_ENERGY_COST = 0.05
TRIBE_THRESHOLD = 0.7    # trust 倾向高的 Agent 的信任门槛
EMA_ALPHA = 0.3          # local_norm EMA 平滑系数

# --- 强制参数 ---
LOOT_RATIO = 0.3
LOOT_EFFICIENCY = 2.0
COUNTER_SEVERITY = 0.3
BASE_COERCE_ENERGY = 0.2
BASE_COERCE_WEALTH = 1.0
COERCE_SCALE_FACTOR = 50.0

# --- Power 参数 ---
POWER_A1 = 1.0   # energy 权重
POWER_A2 = 0.5   # wealth 权重
POWER_B1 = 1.0   # 组织规模放大系数
POWER_B2 = 0.05  # 治理成本系数

# --- 组织参数 ---
MIN_ORG_SIZE = 3
PROPOSE_TRUST_THRESHOLD = 0.6
PROPOSE_MARGIN = 0.1
COOLDOWN_BASE = 10.0
BACKOFF_FACTOR = 2.0
JOIN_THRESHOLD = 0.1
EXIT_THRESHOLD = 0.1

# --- 组织默认 rules ---
DEFAULT_RULES = {
    'tax_rate': 0.05,
    'redistribution_ratio': 0.5,
    'public_goods_efficiency': 0.3,
    'internal_coercion_tolerance': 0.2,
    'punishment_severity': 0.3,
    'enforcement_cost_share': 0.5,
    'delegation_rate': 0.5,
    'ideology_strength': 0.0,
    'ideology_extremity': 0.0,
    'entry_barrier': 0.3,
    'exit_penalty': 0.1,
    'external_aggression_bias': 0.3,
    'loot_policy': 0.3,
}

MUTATABLE_KEYS = [
    'tax_rate', 'redistribution_ratio', 'delegation_rate',
    'external_aggression_bias', 'loot_policy',
    'entry_barrier', 'exit_penalty',
]

MUTATION_STEP = 0.05
GRIEVANCE_THRESHOLD = 0.3

# --- 制度突变触发阈值 ---
EFFICIENCY_THRESHOLD = 0.3
MIGRATION_THRESHOLD = 0.2

# --- 规则范围 ---
RULES_MIN = {k: 0.0 for k in DEFAULT_RULES}
RULES_MAX = {
    'tax_rate': 0.5,
    'redistribution_ratio': 1.0,
    'public_goods_efficiency': 1.0,
    'internal_coercion_tolerance': 1.0,
    'punishment_severity': 1.0,
    'enforcement_cost_share': 1.0,
    'delegation_rate': 1.0,
    'ideology_strength': 1.0,
    'ideology_extremity': 1.0,
    'entry_barrier': 1.0,
    'exit_penalty': 1.0,
    'external_aggression_bias': 1.0,
    'loot_policy': 1.0,
}

# --- 网络迁移 ---
REWIRE_RATIO = 0.3
REWIRE_DECAY = 0.3
INITIAL_REWIRE_TRUST = 0.3
