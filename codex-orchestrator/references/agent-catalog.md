# Agent 角色速查表

## 角色总览

| 角色 | 文件 | 核心能力 | 产出物 |
|------|------|---------|--------|
| architect | `agents/architect.md` | 需求分析、模块划分、接口定义、技术选型 | `01_architect_design.md` |
| developer | `agents/developer.md` | 代码实现、Bug 修复、遵循项目约定 | 代码 + `02_developer_changelog.md` |
| reviewer | `agents/reviewer.md` | 架构一致性、安全、性能、代码质量审查 | `03_reviewer_report.md` |
| tester | `agents/tester.md` | 测试设计、边界验证、缺陷报告 | 测试代码 + `04_tester_report.md` |
| researcher | `agents/researcher.md` | 多源调研、方案比较、推荐意见 | `00_researcher_{topic}_findings.md` |
| tech-writer | `agents/tech-writer.md` | API 文档、使用指南、README | `05_techwriter_docs.md` |
| project-lead | `agents/project-lead.md` | 任务拆解、团队组建、进度监控、冲突协调 | `00_project_lead_plan.md` |

## 按场景快速选择

### 新功能开发
```
architect + developer + reviewer [+ tester]
模式：流水线 + 生成-验证
流程：architect 设计 → developer 实现 → reviewer 审查 → tester 验证
```

### 技术调研/选型
```
researcher × 2-4（各关注不同维度）
模式：扇出/扇入
流程：并行调研 → 汇总比较 → 推荐意见
```

### 代码审查
```
reviewer × 2-3（安全/性能/架构 各一个视角）
模式：扇出/扇入
流程：并行审查 → 汇总报告（按严重程度排序）
```

### 大规模重构/迁移
```
project-lead + developer × 2-3
模式：监督者
流程：project-lead 分析 → 分批分配 → 动态再分配 → 逐批验证
```

### 全栈项目
```
architect + developer(前端) + developer(后端) + tester
模式：层级委派
流程：architect 总体设计 → 前后端并行开发 → tester 集成测试
```

### 文档完善
```
tech-writer + researcher
模式：扇出/扇入
流程：researcher 收集信息 → tech-writer 撰写文档
```

### Bug 修复/调查
```
developer + tester
模式：生成-验证
流程：developer 修复 → tester 验证 → 迭代（最多 2 轮）
```

### 项目启动
```
researcher + architect + developer
模式：流水线
流程：researcher 调研 → architect 设计 → developer 搭建骨架
```

## 角色间数据流

箭头表示产出物流向，角色间通过 `_workspace/` 文件传递数据：

```
architect  ──01_architect_design.md──────────→ developer, reviewer, tester
developer  ──02_developer_changelog.md───────→ reviewer, tester
reviewer   ──03_reviewer_report.md───────────→ developer
tester     ──04_tester_report.md─────────────→ developer
researcher ──00_researcher_{topic}_findings.md→ architect
tech-writer──05_techwriter_docs.md───────────→ reviewer
```

## 团队规模指南

| 任务规模 | 推荐人数 | 每人任务数 |
|---------|---------|-----------|
| 小（1-2 关注点） | 不组队 | — |
| 中（3-5 关注点） | 2-3 人 | 3-5 个 |
| 大（6+ 关注点） | 3-5 人 | 4-6 个 |

**原则**：3 个专注的成员 > 5 个分散的成员。宁精勿滥。
