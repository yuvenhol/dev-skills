---
name: cc-orchestrator
version: 1.0.0
description: "通用开发任务编排器。将复杂开发任务拆解为专业 agent 角色并协调协作。当需要'组建团队'、'任务分解'、'多 agent 协作'、'组队开发'、'并行开发'、'团队协作'时使用。后续任务支持：'修改团队'、'调整分工'、'重新执行'、'更新计划'、'仅重新执行某阶段'。对于简单任务或单文件改动，直接完成，仅在复杂度确实需要多角色协作时启用。"
---

# Team Orchestrator — 通用开发任务编排器

将复杂开发任务拆解为专业 agent 角色，选择合适的架构模式，协调 agent 团队协作完成任务。

**核心原则：**
1. Agent 团队是默认执行模式 — 2 人以上时优先使用 TeamCreate
2. 角色定义与编排分离 — agent 定义在 `agents/`，编排逻辑在此 skill
3. 中间产出物统一存放 `_workspace/` — 命名规范 `{阶段}_{agent}_{产出物}.{ext}`

## 何时启用

- 用户明确要求"组队""多 agent 协作""拆解任务""并行推进"
- 任务至少包含 2 个需要不同专业视角的子问题
- 任务需要显式保留中间设计、审查、测试等产出物以便后续追溯

以下情况不要启用本编排器，直接完成：
- 简单问答、单文件小改动、局部 Bug 修复
- 不需要角色分工即可在当前会话中直接完成的任务
- 只是需要一个专家视角，而不是多角色协作

## 执行模式

| 模式 | 适用场景 | 工具 |
|------|---------|------|
| **Agent 团队**（默认） | 2+ agent 需要协作、交叉验证 | TeamCreate + SendMessage + TaskCreate |
| **子 Agent** | 单一任务、仅需结果返回 | Agent 工具 + run_in_background |
| **混合模式** | 各阶段特性不同 | 按阶段切换模式 |

> 详细模式选择指南参照 `references/pattern-selector.md`

## 工作流

### Phase 0: 上下文确认

1. 检查当前项目的 `_workspace/` 目录是否存在
2. 判断执行模式：
   - `_workspace/` **不存在** → 初始执行，进入 Phase 1
   - `_workspace/` **存在** + 用户请求部分修改 → 部分重新执行（仅重跑相关 agent）
   - `_workspace/` **存在** + 全新输入 → 新执行（备份旧 `_workspace/` 为 `_workspace_{YYYYMMDD_HHMMSS}/`）
3. 识别项目技术栈（检查 pyproject.toml / package.json / Cargo.toml / go.mod 等）

### Phase 1: 任务分析

1. 理解用户的任务目标和约束
2. 判定任务性质（新功能 / 调研 / 重构 / 修复 / 文档 / 审查）
3. 估算任务规模：
   - 小（1-2 个关注点）→ 无需组队，子 agent 或直接完成
   - 中（3-5 个关注点）→ 2-3 人团队
   - 大（6+ 个关注点）→ 3-5 人团队
4. 参照 `references/pattern-selector.md` 选择架构模式
5. 参照 `references/agent-catalog.md` 选择 agent 角色组合
6. 判断是否需要显式确认：
   - 需求不清、方案分歧较大、执行成本高或可能影响较大时 → 先向用户确认
   - 用户已明确要求组队执行，且方案清晰、风险可控时 → 直接进入 Phase 2

### Phase 2: 团队组建

1. 根据 Phase 1 分析结果组建团队：
   - `TeamCreate` — 成员引用 `agents/` 目录下的角色定义
   - 所有 agent 显式设置 `model: "opus"`
2. `TaskCreate` 注册子任务：
   - 每个 agent 分配 3~6 个任务
   - 使用 `depends_on` 声明任务依赖关系
3. 创建 `_workspace/` 目录保存中间产出物

### Phase 3: 执行

1. 成员通过共享任务列表认领并执行任务
2. 成员间通过 `SendMessage` 实时协调：
   - 共享发现、讨论冲突、补充遗漏
   - 不必经过 Leader 即可直接通信
3. Leader 通过 `TaskGet` 监控进度，必要时介入协调
4. 产出物保存到 `_workspace/{阶段}_{agent}_{产出物}.{ext}`

### Phase 4: 整合与验证

1. 通过 `Read` 收集所有成员的产出物
2. 检查一致性：
   - 接口定义两侧是否匹配
   - 产出物间是否有矛盾
3. 生成最终产出物
4. 简要质量验证

### Phase 5: 清理与报告

1. 向用户报告完成情况和关键产出物位置
2. `TeamDelete` 清理团队
3. 保留 `_workspace/` 供审计和后续任务使用

## 常用团队模板

### 功能开发
```
architect(1) → developer(1-2) → reviewer(1) + tester(1)
模式：流水线 + 生成-验证
```

### 技术调研
```
researcher(2-4)
模式：扇出/扇入
```

### 代码审查
```
reviewer(2-3)（分别关注安全/性能/架构）
模式：扇出/扇入
```

### 大规模重构
```
project-lead(1) + developer(2-3)
模式：监督者
```

### 全栈开发
```
architect(1) + developer-frontend(1) + developer-backend(1) + tester(1)
模式：层级委派
```

### 文档完善
```
tech-writer(1) + researcher(1)
模式：扇出/扇入
```

## 错误处理

| 情况 | 策略 |
|------|------|
| 单个成员失败 | Leader 通过 SendMessage 确认 → 重启或创建替代 |
| 过半成员失败 | 通知用户确认是否继续 |
| 超时 | 使用已收集的部分结果 |
| 成员间数据冲突 | 标注来源并列，不删除任何一方 |
| 任务状态延迟 | Leader 通过 TaskGet 确认后手动 TaskUpdate |

## 数据传递规范

| 策略 | 方式 | 适用场景 |
|------|------|---------|
| 消息 | SendMessage | 实时协调、轻量反馈 |
| 任务 | TaskCreate/TaskUpdate | 进度跟踪、依赖管理 |
| 文件 | Write/Read `_workspace/` | 结构化产出物（>100行） |
| 返回值 | Agent 工具返回 | 子 Agent 结果收集 |

## 冲突处理协议

1. 数据冲突 → 不删除任何一方，标注来源后并列
2. 设计分歧 → architect 有最终决定权，但需说明理由
3. 实现与设计不一致 → developer 向 architect 报告，由 architect 判断

## 测试场景

### 正常流程：功能开发
1. 用户请求"为项目添加用户认证功能"
2. Phase 1 分析 → 中等规模功能开发 → 流水线模式
3. Phase 2 组建 architect + developer + reviewer 团队
4. Phase 3 按序执行：设计 → 实现 → 审查
5. Phase 4 整合
6. 产出：`_workspace/` 下的设计文档 + 代码 + 审查报告

### 错误流程：开发阻塞
1. Phase 3 中 developer 遇到接口定义不明确
2. developer 向 architect SendMessage 请求澄清
3. architect 补充接口定义并 SendMessage 回复
4. developer 继续实现
