# dev-skills

给 AI 编码助手准备的「随身手册」。沉淀那些每次都得重复一遍的规范、流程和角色约束，让 Codex、Claude Code 们按需翻阅。

## 当前在册

| Skill | 给谁用 | 解决什么问题 |
|-------|--------|--------------|
| `codex-orchestrator` | Codex | 复杂任务编排。靠 `_workspace/` 文件驱动，把活儿派给 architect / developer / reviewer / tester，串行或并行收工。 |
| `cc-orchestrator` | Claude Code | 多 Agent 协作。用 TeamCreate / SendMessage / TaskCreate 组队，分工干活。 |
| `python-dev-standards` | Python 后端 | FastAPI、Pydantic v2、SQLAlchemy async、配置、测试、类型、异常、异步 I/O、统一错误响应、Repository / Service 分层——一份齐活。 |

## 怎么用

1. 命中某个领域 → 先读对应 skill 的 `SKILL.md`。
2. 需要展开细节 / 模板 / 长例子 → 再翻 `references/`。
3. 编排类 skill 自带 `agents/` 存角色；普通规范类不必硬塞。

## 维护约定

- `SKILL.md` 只写触发边界、执行流程、reference 索引——保持轻。
- `references/` 承载完整规范、长示例、模板、决策细节——保持厚。
- 不给单个 skill 加 README / CHANGELOG / 安装说明，除非它真的服务于执行。
- 改规范优先动 reference；只有入口、触发或资源索引变了，才动 `SKILL.md`。
- 增删 skill 记得回来更新上面的表格。
