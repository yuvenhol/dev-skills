---
name: codex-orchestrator
description: "通用开发任务编排器。将复杂开发任务拆解为专业 agent 角色并协调协作。当需要'组建团队'、'任务分解'、'多 agent 协作'、'组队开发'、'并行开发'、'团队协作'时使用。后续任务支持：'修改团队'、'调整分工'、'重新执行'、'更新计划'、'仅重新执行某阶段'。对于简单任务或单文件改动，直接完成，仅在复杂度确实需要多角色协作时启用。"
metadata:
  version: 1.0.0
---

# Team Orchestrator — 通用开发任务编排器（Codex 版）

将复杂开发任务拆解为专业 agent 角色，选择合适的架构模式，通过文件驱动协调完成任务。

**核心原则：**
1. 文件驱动协调 — agent 间通过 `_workspace/` 文件传递数据
2. 顺序/并行子任务 — 通过执行顺序控制依赖关系
3. 中间产出物统一存放 `_workspace/` — 命名规范 `{阶段}_{agent}_{产出物}.{ext}`

## 何时启用

- 用户明确要求“组队”“多 agent 协作”“拆解任务”“并行推进”
- 任务至少包含 2 个需要不同专业视角的子问题
- 任务需要显式保留中间设计、审查、测试等产出物以便后续追溯

以下情况不要启用本编排器，直接完成：
- 简单问答、单文件小改动、局部 Bug 修复
- 不需要角色分工即可在当前会话中直接完成的任务
- 只是需要一个专家视角，而不是多角色协作

## 执行模式

Codex 通过顺序或并行子任务调用 agent 角色。agent 间不直接通信，而是通过文件传递数据。
如果当前环境不适合真实并行或多 agent 委派，则由当前会话按执行顺序串行扮演各角色，仍然使用 `_workspace/` 维护中间产出物和边界。

| 模式 | 适用场景 | 方式 |
|------|---------|------|
| **顺序执行** | 阶段间有依赖 | 按顺序依次调用各角色 |
| **并行执行** | 独立任务 | 同时启动多个角色 |
| **迭代执行** | 生成-验证 | 循环调用直到通过验证（最多 2 轮） |

> 详细模式选择指南参照 `references/pattern-selector.md`

## 工作流

### Phase 0: 上下文确认

1. 检查当前项目的 `_workspace/` 目录是否存在
2. 判断执行模式：
   - `_workspace/` **不存在** → 初始执行，进入 Phase 1
   - `_workspace/` **存在** + 用户请求部分修改 → 部分重新执行（仅重跑相关角色）
   - `_workspace/` **存在** + 全新输入 → 新执行（备份旧 `_workspace/` 为 `_workspace_{YYYYMMDD_HHMMSS}/`）
3. 识别项目技术栈（检查 pyproject.toml / package.json / Cargo.toml / go.mod 等）

### Phase 1: 任务分析

1. 理解用户的任务目标和约束
2. 判定任务性质（新功能 / 调研 / 重构 / 修复 / 文档 / 审查）
3. 估算任务规模：
   - 小（1-2 个关注点）→ 单角色直接完成
   - 中（3-5 个关注点）→ 2-3 个角色
   - 大（6+ 个关注点）→ 3-5 个角色
4. 参照 `references/pattern-selector.md` 选择架构模式
5. 参照 `references/agent-catalog.md` 选择角色组合
6. 判断是否需要显式确认：
   - 需求不清、方案分歧较大、执行成本高或可能影响较大时 → 先向用户确认
   - 用户已明确要求组队执行，且方案清晰、风险可控时 → 直接进入 Phase 2

### Phase 2: 执行计划

1. 根据 Phase 1 分析结果制定执行计划
2. 将计划写入 `_workspace/00_project_lead_plan.md`：
   - 角色列表和职责
   - 执行顺序和依赖关系
   - 每个角色的输入文件和输出文件路径
3. 创建 `_workspace/` 目录
4. 若不使用真实多 agent，也要在计划中明确“由当前会话串行执行哪些角色”

### Phase 3: 执行

按执行计划依次或并行调用各角色：

**顺序任务示例（流水线）：**
```
1. 调用 architect → 读取需求 → 输出 _workspace/01_architect_design.md
2. 调用 developer → 读取设计文档 → 输出代码 + _workspace/02_developer_changelog.md
3. 调用 reviewer  → 读取设计 + changelog + 代码 → 输出 _workspace/03_reviewer_report.md
4. 调用 developer → 读取审查报告 → 修改代码 → 更新 changelog
5. 调用 tester    → 读取设计 + changelog + 代码 → 输出 _workspace/04_tester_report.md
```

**并行任务示例（扇出/扇入）：**
```
1. 并行调用 researcher-A + researcher-B
   → 各自输出 _workspace/00_researcher_{topic}_findings.md
2. 汇总所有 findings 文件 → 生成整合报告
```

若当前环境不适合真实并行：
```
1. researcher-A 先完成并写文件
2. researcher-B 基于同一输入独立完成并写文件
3. 最后统一汇总
```

**迭代任务示例（生成-验证）：**
```
1. 调用 developer → 输出代码
2. 调用 reviewer  → 审查 → PASS? 结束 : FIX?
3. 调用 developer → 修改 → 回到步骤 2（最多 2 轮）
```

每个角色执行时：
- 读取计划中指定的输入文件
- 执行任务
- 将产出物写入 `_workspace/{阶段}_{agent}_{产出物}.{ext}`
- 若为同一会话串行扮演多个角色，必须显式切换视角，并以上一角色产出物作为下一角色输入，避免在脑中“跳步”

### Phase 4: 整合与验证

1. 读取所有角色的产出物
2. 检查一致性：
   - 接口定义两侧是否匹配
   - 产出物间是否有矛盾
3. 生成最终产出物
4. 简要质量验证

### Phase 5: 报告

1. 向用户报告完成情况和关键产出物位置
2. 保留 `_workspace/` 供审计和后续任务使用

## 常用执行模板

### 功能开发
```
architect → developer → reviewer → developer(修改) → tester
模式：顺序执行 + 迭代（审查修改）
```

### 技术调研
```
researcher-A | researcher-B | researcher-C（并行）→ 汇总
模式：并行执行 → 汇总
```

### 代码审查
```
reviewer-security | reviewer-performance | reviewer-architecture（并行）→ 汇总报告
模式：并行执行 → 汇总
```

### 大规模重构
```
project-lead(计划) → developer-1 | developer-2(并行) → 逐批验证
模式：顺序 + 并行 + 迭代
```

### 全栈开发
```
architect → developer-frontend | developer-backend(并行) → tester
模式：顺序 + 并行 + 顺序
```

### 文档完善
```
tech-writer + researcher（顺序或并行）
模式：并行执行 → 顺序整合
```

## 错误处理

| 情况 | 策略 |
|------|------|
| 某角色产出物缺失 | 检查 blockers 文件，确定原因后重新调用 |
| 产出物间数据冲突 | 标注来源并列，不删除任何一方 |
| 角色执行失败 | 重试一次，仍失败则跳过并在整合时标注 |
| 超时 | 使用已收集的部分结果，在报告中标注未完成项 |
| 关键阻塞 | 写入 blockers 文件，通知用户确认 |

## 数据传递规范

所有 agent 间数据传递通过文件完成：

| 文件 | 写入者 | 读取者 |
|------|--------|--------|
| `_workspace/00_project_lead_plan.md` | project-lead | 所有角色 |
| `_workspace/00_researcher_{topic}_findings.md` | researcher | architect |
| `_workspace/01_architect_design.md` | architect | developer, reviewer, tester |
| `_workspace/02_developer_changelog.md` | developer | reviewer, tester |
| `_workspace/03_reviewer_report.md` | reviewer | developer |
| `_workspace/04_tester_report.md` | tester | developer |
| `_workspace/05_techwriter_docs.md` | tech-writer | reviewer |

## 冲突处理协议

1. 数据冲突 → 不删除任何一方，标注来源后并列
2. 设计分歧 → architect 有最终决定权，但需说明理由
3. 实现与设计不一致 → 在 changelog 中标注差异，由 architect 判断
