# Run Book 文件地图

> 从 a3/bot_civ 提取的通用协作知识库，适用于任何新项目复用。
> 与具体项目无关，聚焦：流程、角色、错题本、复盘。

---

## 快速导航

| 想做什么 | 去哪里 |
|----------|--------|
| 了解完整开发流程 | [workflows/development-workflow.md](workflows/development-workflow.md) |
| 查看角色分工 | [personas/roles.md](personas/roles.md) |
| 查错题本（必读入口） | [error-books/_index.md](error-books/_index.md) → [error-books/flow-rules.md](error-books/flow-rules.md) |
| 查某次 bug 复盘 | [postmortems/](postmortems/) |
| 多终端协作怎么搞 | [workflows/multi-terminal-collaboration.md](workflows/multi-terminal-collaboration.md) |
| Agent 团队管理 | [runbooks/agent-team-management.md](runbooks/agent-team-management.md) |

---

## 目录结构

```
run_book/
├── FILE_MAP.md              ← 你在这里
│
├── workflows/               ← 流程 & 检查清单
│   ├── development-workflow.md      # 四方协作完整开发流程（阶段0→1→2→3）
│   ├── debate-workflow.md           # 协作讨论流程（脑暴 + 评审两种模式）
│   ├── integration-workflow.md      # 集成联调流程
│   ├── multi-terminal-collaboration.md  # 多终端协作流程
│   ├── agent-team-guide.md          # Agent 团队使用指南
│   ├── decision-authority-matrix.md # 决策权限矩阵（谁能拍板什么）
│   ├── checklist-milestone-gate.md  # 里程碑门控检查表（IR→SR→AR）
│   ├── checklist-code-change.md     # 代码变更 6 步检查表
│   ├── checklist-st.md              # 系统测试检查表
│   └── checklist-error-landing.md   # 错误归因检查表（含决策树）
│
├── personas/                ← 角色定义
│   ├── roles.md                     # 角色索引 & 协作原则（入口）
│   ├── architect.md                 # 架构师
│   ├── pm.md                        # 项目经理
│   ├── developer.md                 # 开发者
│   ├── tech-lead.md                 # 技术负责人
│   ├── qa-lead.md                   # 测试经理
│   ├── discussion-expert.md         # 讨论专家
│   ├── recorder.md                  # 记录员
│   ├── human-proxy-pm.md            # 人类替身 PM
│   └── human-proxy-knowledge.md     # 人类替身知识库
│
├── error-books/             ← 错题本（80+ 条经验教训）
│   ├── _index.md                    # ⭐ 错题本总索引（必读入口）
│   ├── flow-rules.md                # ⭐ 流程规则索引（必读）
│   ├── flow-gate.md                 # 门控违规类（DEV-4, 32, 33, 34, 41, 42, 43）
│   ├── flow-code-habit.md           # 编码习惯类（DEV-6, 24, 29, 47）
│   ├── flow-design.md               # 设计阶段类（DEV-38, 40, 44, 45）
│   ├── flow-brainstorm.md           # 脑暴阶段类（DEV-46, 48, 49, 50, 51）
│   ├── tool-rules.md                # 工具使用类（DEV-3, 8, 12, 13, 16, 31, 35, 36）
│   ├── interface-rules.md           # 接口规范类（DEV-1, 2, 11c）
│   ├── common-mistakes.md           # 跨角色通用错误
│   ├── error-book-dev.md            # 开发者专属错题
│   ├── error-book-pm.md             # PM 专属错题
│   ├── error-book-qa.md             # QA 专属错题
│   ├── error-book-debate.md         # 讨论专属错题
│   ├── error-book-recorder.md       # 记录员专属错题
│   ├── backend-agent.md             # 后端 Agent 错误（DEV-11b, 37, 38 + BUG 系列）
│   ├── backend-db.md                # 后端数据库错误（DEV-10c, 10b + BUG 系列）
│   ├── backend-api-env.md           # 后端 API/环境错误（DEV-27 + BUG 系列）
│   ├── frontend-react.md            # 前端 React 错误（DEV-9, 10f, 15 + BUG 系列）
│   └── frontend-ui.md               # 前端 UI 错误（DEV-8f, 11f, 12f, 14, 39 + BUG 系列）
│
├── postmortems/             ← 复盘报告（17 份）
│   ├── postmortem-dev-38.md         # DEV-38 复盘
│   ├── postmortem-dev-40.md         # DEV-40 复盘
│   ├── postmortem-dev-bug-*.md      # DEV-BUG 系列复盘（6,7,9,10,11,12,13,14,15,16,17）
│   ├── postmortem-common-13.md      # COMMON-13 复盘
│   ├── reference-catcafe-analysis.md    # CatCafe 项目分析参考
│   ├── reference-catcafe-lessons.md     # CatCafe 项目教训参考
│   ├── reference-civitas2-analysis.md   # Civitas2 项目分析参考
│   └── reference-maibot-analysis.md     # MaiBot 项目分析参考
│
└── runbooks/                ← 操作手册
    ├── trial-run-complete-workflow.md    # 完整流程试跑指南
    ├── agent-team-management.md         # Agent 团队管理手册
    ├── layered-progress-guide.md        # 分层进度记录指南
    ├── model-selection.md               # 模型选择指南
    └── token-optimization.md            # Token 优化指南
```

---

## 新项目接入指南

1. 将本 `run_book/` 目录复制到新项目中
2. 在新项目的 CLAUDE.md 或入口文件中引用本地图：
   ```
   协作知识库见 run_book/FILE_MAP.md
   ```
3. 按需加载：
   - 开始开发前 → 读 `workflows/development-workflow.md`
   - 分配角色时 → 读 `personas/roles.md` + 对应角色文件
   - 每次编码前 → 读 `error-books/_index.md` + `flow-rules.md`
   - 出 bug 后 → 查 `error-books/` 对应模块 + `postmortems/`

---

## 文件统计

| 分类 | 文件数 | 说明 |
|------|--------|------|
| 流程 & 检查清单 | 10 | 开发全生命周期流程 + 4 份 checklist |
| 角色定义 | 10 | 8 个角色 + 索引 + 知识库 |
| 错题本 | 19 | 80+ 条错误记录，按模块分类 |
| 复盘报告 | 17 | 详细 bug 分析 + 3 份项目参考 |
| 操作手册 | 5 | 团队管理、进度记录、模型选择等 |
| **合计** | **61** | |
