---
name: python-dev-standards
description: Python 后端开发规范。用于编写、审查、重构或初始化 Python 后端项目，尤其是 FastAPI、Pydantic v2、SQLAlchemy async、异步 I/O、配置管理、测试、统一错误响应、Repository/Service 分层和工具链配置。
---

# Python 开发规范

## 使用方式

- 先判断目标是新项目还是既有项目。新项目按本规范默认值初始化；既有项目优先遵循当前 `pyproject.toml`、目录结构、运行环境和 CI 约束，除非用户明确要求升级或重构。
- 需要具体规则、代码示例或模板时，读取 `references/python-dev-standards.md`。该文件是本 skill 的完整规范细则。
- 维护本仓库时，根目录 `README.md` 只说明 `dev-skills` 仓库定位；Python 规范正文以 `references/python-dev-standards.md` 为准。
- 生成或修改代码时，优先保持项目现有模式，只在没有既有约束时采用本规范默认结构。

## 核心判定

- 项目结构：默认使用 `src-layout`，按业务场景拆分 `domain/<scene>/`；前端独立 SPA 时使用 `backend/` 与 `frontend/` 分离。
- 配置管理：使用 `pydantic-settings`；提交 `config/.env.base` 和 `.env.example`；根目录 `.env` 只用于本地覆盖且不提交；生产差异通过系统环境变量注入。
- API 与 Service 边界：简单 CRUD / 简单只读路由可以通过依赖注入调用 Repository；包含业务规则、事务边界、跨 Repository 编排或跨资源流程时必须进入 Service 层。
- 错误响应：业务错误使用自定义异常和全局异常处理器，API 错误响应统一为 `code` / `message` / `detail`；不要在路由中散写非统一结构的 `HTTPException`。
- Python 版本：新项目默认 Python 3.14；既有项目以当前项目配置和 CI 版本为准，不因本规范自动升级。
- 测试：单元测试保持可重复、隔离、快速；避免网络、文件系统和数据库 I/O；优先轻量替身，少用 mock；不得删除业务数据。
- 异步 I/O：FastAPI 路由优先 `async def`，但严禁在 async 函数中直接调用阻塞 I/O；HTTP/DB/Redis 等外部调用优先使用异步客户端并复用连接池。
- 数据库：Repository 只做单一数据操作，不提交事务；事务边界由 Service 控制；schema 变更必须通过 Alembic 迁移。

## 按任务读取细则

| 任务 | 读取章节 |
|------|----------|
| 初始化 Python 后端项目 | `1. 项目架构`、`2. 配置管理`、`12. 工具链配置模板` |
| 开发 FastAPI 接口 | `4. FastAPI 开发`、`10. 统一错误响应`、必要时读 `11. 数据库与 Repository` |
| 设计配置或环境变量 | `2. 配置管理` |
| 编写或调整测试 | `3. 测试规范` |
| 做类型、导入、命名清理 | `5. 类型注解`、`7. 导入规范`、`8. 命名规范` |
| 审查异常处理 | `6. 异常处理`、`10. 统一错误响应` |
| 处理异步、并发或外部调用 | `9. 异步 I/O 与并发` |
| 设计 Repository、事务或迁移 | `11. 数据库与 Repository` |

## 执行准则

- 引用规范时给出具体章节或文件位置，避免只说“按规范”。
- 改既有项目时先读本地代码和配置，再决定适用哪些规范；不要为了符合模板做无关迁移。
- 当规范与用户明确要求冲突时，先指出冲突和影响，再按用户确认的方向执行。
- 完成代码改动后，优先运行项目已有的 lint、type check 和相关测试；文档或规范改动至少做结构和关键词检查。
