# dev-skills

`dev-skills` 是面向 AI Coding 的开发技能集合仓库。仓库按 skill 组织可复用的工程规范、工作流和检查清单，让 Codex、Claude Code 等 AI 编码助手在执行开发任务时有明确、可引用、可维护的项目级约束。

## 定位

本仓库不承载单个项目的业务代码，而是沉淀开发过程中的通用能力：

- 开发规范：目录结构、分层边界、命名、导入、异常处理、测试和工具链配置。
- 工程工作流：初始化、重构、审查、验证和交付时可复用的执行步骤。
- AI 执行约束：把容易产生歧义的工程口径写成明确规则，降低 AI 生成代码时的偏差。
- 参考资料：较长的规范正文放入 skill 的 `references/`，避免主入口过长。

## 目录结构

```text
dev-skills/
├── README.md
└── skills/
    └── python-dev-standards/
        ├── SKILL.md
        └── references/
            └── python-dev-standards.md
```

## 当前 Skills

| Skill | 说明 |
|-------|------|
| `python-dev-standards` | Python 后端开发规范，覆盖 FastAPI、Pydantic v2、SQLAlchemy async、配置管理、测试、类型注解、异常处理、异步 I/O、统一错误响应、Repository/Service 分层和工具链配置。 |

## Skill 编写约定

每个 skill 应保持入口简洁，详细内容按需放入 `references/`：

```text
skills/<skill-name>/
├── SKILL.md
└── references/
    └── <topic>.md
```

约定：

- `SKILL.md` 只放触发说明、使用方式、核心判断和引用索引。
- `references/` 放完整规范、长示例、模板和扩展说明。
- 不为 skill 额外添加 README、CHANGELOG、安装说明等辅助文件，除非确有执行价值。
- 更新规范时，先保证 skill 主入口和 reference 的职责清晰，再同步相关引用路径。

## 使用方式

每个 skill 的入口是 `skills/<skill-name>/SKILL.md`，扩展规范放在 `references/`。当任务涉及对应领域时，AI 应先读取 `SKILL.md`；需要具体规则、示例或模板时，再读取 `references/` 下的对应文件。

以当前仓库内的 Python 规范为例：

```text
skills/python-dev-standards/SKILL.md
skills/python-dev-standards/references/python-dev-standards.md
```


## 维护原则

- 优先保证 AI 阅读顺畅、无歧义，而不是追求文档形式完整。
- 规则要能直接指导执行，避免只写抽象原则。
- 对既有项目保持克制：先读项目现状，再决定适用哪些规范。
- 当规范之间有冲突时，以更具体、更靠近执行场景的规则为准，并在文档中消除冲突。
