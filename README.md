# dev-skills

面向 AI Coding 的 skill 集合仓库。这里不放业务代码，也不做复杂安装脚手架，只沉淀可复用的开发规范、编排流程和角色约束，供 Codex、Claude Code 等 AI 编码助手按需读取。

## Skills

| Skill | 适用对象 | 用途 |
|-------|----------|------|
| `codex-orchestrator` | Codex | 复杂开发任务编排。通过 `_workspace/` 文件驱动，把任务拆解给 architect、developer、reviewer、tester 等角色顺序或并行完成。 |
| `cc-orchestrator` | Claude Code | Claude Code 多 Agent 编排。使用 TeamCreate / SendMessage / TaskCreate 组织角色团队协作。 |
| `python-dev-standards` | Python 后端项目 | Python 后端开发规范，覆盖 FastAPI、Pydantic v2、SQLAlchemy async、配置、测试、类型、异常、异步 I/O、统一错误响应和 Repository/Service 分层。 |

## 使用方式

- 任务触发某个领域时，先读取对应 skill 的 `SKILL.md`。
- 需要细则、示例、模板或长说明时，再读取该 skill 的 `references/`。
- 编排类 skill 自带 `agents/`，用于保存角色定义；普通规范类 skill 不需要强行添加 `agents/`。
- 本仓库的 skill 包直接放在根目录，不再额外包一层 `skills/`。

## 维护约定

- `SKILL.md` 保持轻量，只写触发边界、执行流程和 reference 索引。
- `references/` 承载完整规范、长示例、模板和决策细节。
- 不给单个 skill 额外添加 README、CHANGELOG、安装说明等辅助文件，除非它们直接服务执行。
- 修改规范时优先更新 reference；只有入口、触发方式或资源索引变化时才改 `SKILL.md`。
- 增删 skill 时同步更新本 README 的 Skills 表。
