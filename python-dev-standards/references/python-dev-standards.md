<!-- Full reference for the python-dev-standards skill. -->

# Python 开发规范

## 规范定位

本规范用于指导 AI 生成更规范、可维护、可测试的 Python 代码。它既可以在项目初始化时作为脚手架和架构约束使用，也可以在完成编码后作为重构检查清单，用于统一目录结构、配置管理、类型注解、异常处理、测试方式和工具链配置。

核心目标：
- 让 AI 生成的代码默认具备清晰分层、稳定边界和一致风格
- 减少硬编码、隐式依赖、异常吞没、阻塞 I/O 等常见工程问题
- 让项目在初始化、迭代开发、代码审查和后续重构阶段都有统一依据

## 1. 项目架构

### 标准目录结构

```
project_root/
├── src/
│   └── project_name/
│       ├── __init__.py        # 包初始化，暴露 SRC_PATH、ROOT_PATH
│       ├── core/              # 核心公共能力
│       │   ├── config.py
│       │   ├── http_client.py
│       │   ├── logging.py
│       │   └── observability.py
│       ├── api/               # FastAPI 应用入口
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── routes/
│       │   └── middleware/
│       ├── domain/            # 业务领域（按场景隔离）
│       │   ├── user/
│       │   │   ├── models.py
│       │   │   ├── service.py
│       │   │   ├── repository.py
│       │   │   └── schemas.py
│       │   └── order/
│       └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── config/
│   └── .env.base
├── .env.example
├── pyproject.toml
└── README.md
```

### 根包路径常量

`src/project_name/__init__.py` 作为根包初始化文件，必须嵌入项目路径常量，用于统一定位 `src` 包目录和项目根目录：

```python
import os

SRC_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT_PATH = os.path.dirname(os.path.dirname(SRC_PATH))
```

约定：
- `SRC_PATH` 指向 `src/project_name/`
- `ROOT_PATH` 指向 `project_root/`
- 其他模块需要定位项目文件时从根包导入 `ROOT_PATH`，不要在各模块重复计算项目根目录
- `ROOT_PATH` 是字符串路径，路径拼接使用 `os.path.join(ROOT_PATH, "...")`

### Web 页面（可选）

纯后端模式可以直接提供 web 页面：在项目根新增 `static/` 目录存放 HTML / CSS / JS，由 FastAPI 静态托管；页面通过 fetch 调用 `/api/*` 完成动态交互，按需配合 htmx / Alpine.js 等轻量库。如确需服务端渲染再引入模板引擎（Jinja2、Mako 等），本规范不做限定。

在标准结构上的最小增量：

```
project_root/
├── src/project_name/...      # 沿用上面"标准目录结构"
├── static/                   # web 页面，与 src/ 同级
│   ├── index.html
│   ├── css/
│   └── js/
├── tests/
├── config/
└── ...
```

挂载（在所有 API 路由注册之后）：

```python

app.mount("/", StaticFiles(directory=os.path.join(ROOT_PATH, "static"), html=True), name="web")
```

约定：
- 静态资源统一放 `static/`，与 `src/` 同级；不预先划分子目录
- 页面只通过 `/api/*` 与后端通信，不直接访问后端内部状态
- 复杂前端交互改用前后端分离变体

### 变体：前后端分离

适用于前端为独立 SPA、独立部署的项目。仓库顶层划分两个工程，各自维护各自的规范：

```
project_root/
├── backend/         # 后端工程，内部沿用上面的"标准目录结构"
├── frontend/        # 前端工程，结构由前端规范决定，不在本文档范围
└── README.md
```

后端约束：
- 所有路由必须在 `/api` 前缀下；破坏性变更走新版本前缀（如 `/api/v2`）
- 响应必须用 `*Response` schema 序列化，禁止直接返回 ORM 实体
- CORS 仅在开发环境开放；生产通过反向代理同源部署

### 选型建议

默认使用**标准目录结构**。前端独立成 SPA 时用前后端分离变体。

### 分层职责

#### core 层（公共能力）
- 配置管理（`config.py`）
- HTTP 客户端封装
- 日志配置与可观测性
- LLM 调用封装（如适用）
- 通用工具函数
- **不依赖业务逻辑**

#### api 层（应用入口）
- 应用初始化与生命周期管理
- 路由注册
- 中间件配置
- 全局异常处理

#### domain 层(业务领域)
- `models.py`：领域模型（Pydantic 模型、数据类）
- `service.py`：业务逻辑
- `repository.py`：数据访问层
- `schemas.py`：API 请求/响应模型

### 核心原则

- ✅ **必须**使用 `src-layout`（代码放在 `src/` 目录下）
- ✅ **必须**按业务场景隔离子模块，避免单一巨型模块
- ✅ **允许**API 层在简单 CRUD、简单只读、依赖装配或 composition root 中通过依赖注入访问 Repository
- ✅ **必须**将业务规则、事务边界、跨 Repository 编排或跨资源流程放入 Service 层
- ✅ **推荐**使用依赖注入管理层级间依赖

### 示例代码

#### 正确的分层示例

```python
class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def get_user(self, user_id: int) -> User | None:
        return await self._repository.find_by_id(user_id)


router = APIRouter()
async def get_user_service() -> UserService:
    # 依赖注入
    return UserService(repository=UserRepository())
@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_user(user_id)
    if not user:
        raise UserNotFoundError(detail={"user_id": user_id})
    return UserResponse.model_validate(user)
```

#### 不推荐示例

```python
# ❌ 错误: 路由层承载事务和跨 Repository 编排
@router.post("/balance/transfer")
async def transfer_balance(request: TransferBalanceRequest) -> None:
    async with transaction() as session:
        users = UserRepository(session)
        orders = OrderRepository(session)
        ...
```

## 2. 工具链配置模板

### pyproject.toml

以下模板面向新项目，只包含通用工程元信息、测试、Pyright 和 Ruff 配置；业务依赖按项目实际需要补充。既有项目应以当前 Python 版本和工具链约束为准，不因套用模板自动升级。

```toml
[project]
name = "project-name"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = "~=3.14.0"
dependencies = []

[dependency-groups]
dev = [
    "pyright>=1.1.0",
    "pytest>=9.0.0",
    "pytest-asyncio>=1.3.0",
    "ruff>=0.14.0",
]

[tool.pytest.ini_options]
testpaths = "tests"
python_files = "tests.py test_*.py *_tests.py"
log_cli = true
log_cli_level = "DEBUG"
log_cli_format = "%(asctime)s %(levelname)s %(filename)s [line:%(lineno)d] - %(message)s"
log_cli_date_format = "%H:%M:%S"

[build-system]
build-backend = "hatchling.build"
requires = ["hatchling"]

[tool.pyright]
typeCheckingMode = "standard"
pythonVersion = "3.14"
include = ["src", "tests"]
exclude = [".git", ".venv", "__pycache__", "build", "dist"]
venvPath = "."
venv = ".venv"

[tool.ruff]
line-length = 100
include = ["src/**/*.py", "tests/**/*.py"]
exclude = [".git", ".venv", "__pycache__", "build", "dist"]
preview = true

[tool.ruff.lint]
select = [
    "E",       # pycodestyle errors
    "W",       # pycodestyle warnings
    "F",       # pyflakes
    "I",       # isort
    "B",       # flake8-bugbear
    "C4",      # flake8-comprehensions
    "UP",      # pyupgrade
    "TID252",  # Disallow relative imports
    "PLC0415", # import-outside-top-level
]
ignore = [
    "B008", # do not perform function calls in argument defaults
    "W191", # indentation contains tabs
]
```

## 3. 配置管理

### 配置文件结构

```
config/
└── .env.base       # 基础默认配置（可提交，不含密钥）

.env.example        # 配置模板（必须提交）
.env                # 本地覆盖配置（不提交）
```

### 配置优先级（从低到高）

1. `Settings` 类字段默认值
2. `config/.env.base`（基础配置）
3. 项目根目录 `.env`（本地覆盖）
4. 系统环境变量（最高优先级）

### 环境标识

`ENV` 只是运行环境标识（如 `dev` / `fat` / `prod`），不用于加载仓库内的环境专属配置文件。环境差异配置由运行平台通过系统环境变量注入；本地开发差异使用项目根目录 `.env` 覆盖。

### 配置类定义

```python


def _load_env_file(path: str | PathLike[str]) -> dict[str, str]:
    return {
        key: value
        for key, value in dotenv_values(path).items()
        if value is not None
    }
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    ENV: str = "dev"
    DEBUG: bool = False
    LOG_LEVEL: str = "info"
    SERVICE_NAME: str = "my-service"
raw_config = {
    **_load_env_file(os.path.join(ROOT_PATH, "config/.env.base")),
    **_load_env_file(os.path.join(ROOT_PATH, ".env")),
    **os.environ,
}

SETTINGS = Settings(**raw_config)
```

### 使用方式

```python
# ✅ 正确: 导入全局配置

def connect_database():
    return create_engine(SETTINGS.DATABASE_URL)

if SETTINGS.DEBUG:
    print("Debug mode enabled")

# ❌ 错误: 硬编码配置
DATABASE_URL = "postgresql://localhost/mydb"

# ❌ 错误: 直接读取环境变量
debug = os.getenv("DEBUG")  # 应该使用 SETTINGS.DEBUG
```

### 配置文件示例

```bash
# config/.env.base（基础配置）
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# .env.example（配置模板，不写真实密钥）
DATABASE_URL=
REDIS_URL=
SECRET_KEY=

# .env（本地覆盖，不提交）
DEBUG=true
DATABASE_URL=postgresql://localhost/mydb_dev
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-key-change-in-production
```

### 核心原则

- ✅ **必须**使用 `pydantic-settings` 管理配置
- ✅ **必须**提供 `.env.example` 说明所有必需变量
- ❌ **禁止**提交项目根目录 `.env`
- ✅ **必须**通过系统环境变量注入生产环境差异配置
- ❌ **禁止**硬编码密钥、令牌或凭证
- ❌ **禁止**将生产环境密钥提交到版本控制
- ✅ **推荐**使用 `Field` 添加描述和验证规则

## 4. 测试规范

### 核心原则

#### 单元测试
- 测试单个函数或方法的行为
- 必须可重复、可隔离、快速执行
- 避免网络 I/O、文件系统 I/O、数据库访问
- **不得删除库表或业务数据**
- **尽量不使用 mock**，优先使用真实实现或轻量替身

#### 集成测试
- 测试多个组件的协作
- 可以访问数据库、外部 API、文件系统
- 使用测试数据库或容器化环境

### 单元测试示例

```python

# ✅ 正确: 使用轻量替身而不是 mock
class FakeUserRepository:
    """测试用的假 Repository。"""

    def __init__(self) -> None:
        self._users: dict[int, User] = {}

    async def find_by_id(self, user_id: int) -> User | None:
        return self._users.get(user_id)

    async def save(self, user: User) -> None:
        self._users[user.id] = user
@pytest.fixture
def fake_repository() -> FakeUserRepository:
    return FakeUserRepository()
@pytest.fixture
def user_service(fake_repository: FakeUserRepository) -> UserService:
    return UserService(repository=fake_repository)
@pytest.mark.asyncio
async def test_get_user_success(
    user_service: UserService,
    fake_repository: FakeUserRepository,
):
    # Arrange
    user = User(id=1, name="Alice", email="alice@example.com")
    await fake_repository.save(user)

    # Act
    result = await user_service.get_user(user_id=1)

    # Assert
    assert result is not None
    assert result.name == "Alice"
```

### 执行测试

```bash
# 测试特定文件
uv run pytest tests/unit/test_user_service.py

# 运行所有单元测试
uv run pytest tests/unit/
```

## 5. FastAPI 开发

### 核心原则

- 完整类型注解（新项目默认 Python 3.14；既有项目遵循项目当前 Python 版本）
- 使用 Pydantic v2 进行验证
- 使用 `Annotated` + `Depends` 进行依赖注入
- 优先使用 `async def`

### 路由命名规范

所有业务 API 对外必须挂载在 `/api` 前缀下。路由函数或 `APIRouter` 内部可以只写对象/动作路径，由应用入口统一添加 `/api` 前缀。

**格式**：`/object/action`（对象/动作）
**风格**：全小写，kebab-case

```python
# ✅ 正确
@router.post("/user/create")    # 对外路径: /api/user/create
@router.get("/order/list")      # 对外路径: /api/order/list
@router.post("/image/enhance")  # 对外路径: /api/image/enhance

# ❌ 错误
@router.post("/create_user")
@router.get("/getOrders")
```

```python
app = FastAPI()
app.include_router(user.router, prefix="/api")
```

### Pydantic v2 模型定义

```python

class UserCreate(BaseModel):
    """创建用户请求模型。"""

    username: Annotated[str, Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="用户名",
        examples=["john_doe"],
    )]
    email: Annotated[EmailStr, Field(
        description="邮箱地址",
        examples=["alice@example.com"],
    )]
    password: Annotated[str, Field(
        min_length=8,
        max_length=128,
        description="密码",
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("密码必须包含至少一个大写字母")
        return v
```

### 依赖注入

```python

async def get_current_user(token: str) -> User:
    ...
CurrentUser = Annotated[User, Depends(get_current_user)]
@app.post("/user/create")
async def create_user(
    user: UserCreate,
    current_user: CurrentUser,
) -> UserResponse:
    ...
```

## 6. 类型注解

### Python 版本口径

新项目默认使用 Python 3.14；既有项目以当前 `pyproject.toml`、Pyright 配置和 CI 运行版本为准。除非用户明确要求升级，否则不要仅因本规范修改项目的 Python 版本。

### 核心原则

- 所有公共接口必须有完整类型注解
- 使用目标项目支持的最新 Python 类型语法
- 使用 `|` 而不是 `Union`
- 使用 `| None` 而不是 `Optional`

### 基本类型注解

```python

def greet(name: str) -> str:
    return f"Hello, {name}!"
def calculate_total(prices: list[float], tax_rate: float = 0.1) -> float:
    subtotal = sum(prices)
    return subtotal * (1 + tax_rate)
```

### Union 和 Optional

```python
# ✅ 正确: 使用 |
def process(data: str | int) -> dict[str, Any]:
    ...

# ✅ 正确: 使用 | None
def get_user(user_id: int) -> User | None:
    ...
```

### 泛型（Python 3.12+）

```python
# ✅ Python 3.12+ 语法
def first[T](items: Sequence[T]) -> T | None:
    return items[0] if items else None
class Container[T]:
    def __init__(self, value: T) -> None:
        self.value = value

    def get(self) -> T:
        return self.value
```

### 避免循环导入

```python

if TYPE_CHECKING:
    from project_name.domain.user.repository import UserRepository
class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository
```

## 7. 控制流与代码复杂度

### 核心原则

1. 复杂条件优先拆成有语义的中间变量或私有函数
2. 对同一个状态、命令、事件或领域对象做分支处理时，优先使用 `match/case` 或映射表
3. 保留 `if` 用于范围判断、多个条件组合、需要短路求值或条件之间并非同一维度的场景
4. 禁止在 src 路径使用 assert 做条件判断（仅用于测试代码）

### 禁止在 src 路径使用 assert 做条件判断

```python
# ❌ 错误: 在 src 路径使用 assert（python -O 会跳过）
def process_user_input(data):
    assert data is not None  # 禁止！生产环境会跳过
    return data.upper()

# ✅ 正确: 在业务代码中使用显式检查
def process_user_input(data):
    if data is None:
        raise ValueError("Data cannot be None")
    return data.upper()

# ✅ 正确: 在测试代码中使用 assert
# tests/test_service.py
def test_process_user_input():
    result = process_user_input("hello")
    assert result == "HELLO"  # 测试中可以使用
```

### 多分支判断优先使用 match/case 或映射表

`match/case` 适合对同一对象做结构化分支（字段绑定、类型守卫、多值合并）；映射表适合“枚举/字符串 → 处理函数”这种纯分发场景。

常用模式（每种示意一行即可）：

- 字面量 / 枚举：`case "paid":`、`case OrderStatus.PAID:`
- 多值合并：`case EventType.MESSAGE | EventType.ALERT:`
- 字段绑定：`case SseEvent(event=EventType.FAQ, data=data):`
- 守卫条件：`case ... if isinstance(data, ChatObjectChunk):`
- 默认分支：`case _:`

```python
# ✅ match/case：字段绑定 + 类型守卫 + 多值合并
match event:
    case SseEvent(event=EventType.INTERRUPT):
        mark_interrupted()
    case SseEvent(event=EventType.FAQ, data=data) if isinstance(data, ChatObjectChunk):
        handle_faq(data)
    case SseEvent(event=EventType.MESSAGE_ALL | EventType.ALERT, data=data):
        handle_message(data)
    case _:
        handle_unknown(event)

# ✅ 映射表：纯分发，避免长 if/elif
HANDLERS = {
    OrderStatus.PAID: handle_paid,
    OrderStatus.REFUNDED: handle_refunded,
}
HANDLERS.get(order.status, handle_default)(order)
```

约束：分支按顺序匹配，具体模式靠前；只在处理逻辑一致时用 `|` 合并；`if` 守卫只补充当前模式的额外条件，不要塞复杂业务；分支体超过几行就提取私有函数；不要用裸变量名匹配常量（`case PAID:` 会变成捕获，要用 `OrderStatus.PAID`）；必须显式处理未知分支。

## 8. 异常处理

### 核心原则

1. 使用内置异常类
2. 自定义异常继承自现有异常，类名以 `Error` 结尾
3. 禁止裸露捕获（`except:`），禁止吞掉宽泛异常
4. 最小化 try 块

### 捕获特定异常

```python
# ✅ 正确: 捕获特定异常，最小化 try 块
try:
    value = dictionary[key]
except KeyError:
    logger.warning(f"Key {key} not found")
    value = default_value

# ✅ 正确: 捕获多个特定异常
try:
    result = int(user_input)
except (ValueError, TypeError) as e:
    logger.error(f"Invalid input: {e}")
    result = 0

# ❌ 错误: 裸露捕获，会吞掉 KeyboardInterrupt
try:
    do_something()
except:
    pass

# ❌ 错误: 捕获 Exception 但不记录、不包装、不重新抛出
try:
    do_something()
except Exception:
    pass  # 吞掉了所有异常
```

### 宽泛异常的允许场景

以下边界场景允许捕获 `Exception`，但必须记录、包装或重新抛出：

- 全局异常处理器：记录完整堆栈，返回统一错误响应
- 事务上下文：异常时 rollback，然后重新抛出
- 任务入口或后台任务边界：记录失败原因，避免任务静默退出
- 包装第三方库异常：转换成项目内异常，并使用 `raise ... from e` 保留原始异常链

### 自定义异常

```python
# ✅ 正确: 自定义异常
class DatabaseConnectionError(Exception):
    """数据库连接失败时抛出。"""
class UserNotFoundError(Exception):
    """用户不存在时抛出。"""

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")
class ValidationError(ValueError):
    """数据验证失败时抛出。"""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"{field}: {message}")
```

### 重新抛出异常

```python
# ✅ 正确: 重新抛出时可以捕获广泛异常
try:
    process_data()
except Exception as e:
    logger.exception("Processing failed")
    raise  # 必须重新抛出

# ✅ 正确: 包装异常
try:
    connect_to_database()
except ConnectionError as e:
    raise DatabaseConnectionError("Failed to connect") from e
```

### 最小化 try 块

```python
# ❌ 错误: try 块太大
try:
    user = get_user(user_id)
    validate_user(user)
    process_user(user)
    save_user(user)
    send_notification(user)
except Exception as e:
    logger.error(f"Error: {e}")

# ✅ 正确: 只包裹可能失败的操作
user = get_user(user_id)
validate_user(user)
process_user(user)

try:
    save_user(user)
except DatabaseError as e:
    logger.error(f"Failed to save user: {e}")
    raise

send_notification(user)
```

### 上下文管理器

```python
# ✅ 正确: 使用 with 自动处理资源
with open("file.txt") as f:
    content = f.read()

# ✅ 正确: 自定义上下文管理器
@contextmanager
def database_transaction():
    """数据库事务上下文管理器。"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
# 使用
with database_transaction() as conn:
    conn.execute("INSERT INTO users ...")
```

## 9. 导入规范

### 核心原则

- 使用 `import x` 导入包和模块
- 使用 `from x import y`，其中 `x` 是包前缀，`y` 是模块名
- 禁止相对导入
- 禁止通配符导入
- 使用完整包路径

### 正确的导入方式

```python
# ✅ 正确: 导入模块
from sound.effects import echo
echo.echofilter(...)

# ✅ 正确: 使用别名解决冲突或缩短名称
from absl import flags as absl_flags
from my_project.models import User as ProjectUser

# ✅ 正确: typing 模块例外，可以直接导入类型
from typing import Any
from collections.abc import Mapping, Sequence

# ✅ 正确: 使用完整包路径
from my_project.database import connection
from my_project.models.user import User
```

### 错误的导入方式

```python
# ❌ 错误: 相对导入
from ..models import User
from . import utils

# ❌ 错误: 通配符导入
from my_module import *

# ❌ 错误: 假设模块在当前目录
import models
from user import User
```

### 导入顺序

按照以下顺序组织导入，每组之间空一行：

1. 标准库导入
2. 第三方库导入
3. 本地应用/库导入

```python
# ✅ 正确: 导入顺序
import os
import sys
from pathlib import Path

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from my_project.core.config import SETTINGS
from my_project.domain.user.models import User
```

### 避免循环导入

```python
# ✅ 正确: 使用 TYPE_CHECKING 避免循环导入
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from my_project.domain.user.repository import UserRepository
class UserService:
    def __init__(self, repository: UserRepository) -> None:
        # 类型注解延迟求值，不会在运行时导入
        self._repository = repository
```

### 条件导入

```python
# ✅ 正确: 可选依赖的条件导入
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
def process_array(data):
    if HAS_NUMPY:
        return np.array(data)
    return list(data)
```


## 10. 命名规范

### 命名风格总览

| 类型 | 风格 | 示例 |
|------|------|------|
| 文件名 | `snake_case` | `my_module.py` |
| 包名 | `lowercase` | `mypackage` |
| 类名 | `PascalCase` | `MyClass` |
| 异常 | `PascalCase` + Error | `MyError` |
| 函数/方法 | `snake_case` | `my_function` |
| 变量 | `snake_case` | `my_variable` |
| 常量 | `UPPER_CASE` | `MY_CONSTANT` |
| 私有成员 | `_snake_case` | `_private_var` |

### 类命名

```python
# ✅ 正确: 类名使用 PascalCase
class UserService:
    pass
class DatabaseConnection:
    pass
class HTTPClient:
    pass
# ✅ 正确: 异常类以 Error 结尾
class ValidationError(Exception):
    pass
class DatabaseConnectionError(Exception):
    pass
```

### 函数和变量命名

```python
# ✅ 正确: 函数和变量使用 snake_case
def calculate_total_price(items: list[Item]) -> float:
    total_price = 0.0
    for item in items:
        total_price += item.price
    return total_price
# ✅ 正确: 私有函数和变量使用 _snake_case
def _internal_helper(data: str) -> str:
    return data.upper()
class MyClass:
    def __init__(self) -> None:
        self._private_var = 0
```

### 常量命名

```python
# ✅ 正确: 常量使用 UPPER_CASE
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.example.com"

# ✅ 正确: 私有常量
_DEFAULT_BUFFER_SIZE = 1024
```

### FastAPI 路由命名

详见 [4. FastAPI 开发 - 路由命名规范](#路由命名规范)。

### Pydantic 模型命名

```python
# ✅ 正确: 请求模型以动作结尾
class UserCreate(BaseModel):
    """创建用户请求。"""
    pass
class UserUpdate(BaseModel):
    """更新用户请求。"""
    pass
class OrderQuery(BaseModel):
    """订单查询参数。"""
    pass
# ✅ 正确: 响应模型以 Response 或 Item 结尾
class UserResponse(BaseModel):
    """用户响应。"""
    pass
class UserItem(BaseModel):
    """用户列表项。"""
    pass
# ✅ 正确: 通用模型直接使用名词
class User(BaseModel):
    """用户模型。"""
    pass
```

### 文件命名

```python
# ✅ 正确: 文件名使用 snake_case
user_service.py
database_connection.py
http_client.py

# ❌ 错误
UserService.py
databaseConnection.py
HTTPClient.py
```

### 包命名

```
# ✅ 正确: 包名使用 lowercase
myproject/
    core/
    domain/
    utils/

# ❌ 错误
MyProject/
    Core/
    Domain/
```

### 布尔变量命名

```python
# ✅ 正确: 使用 is_, has_, can_ 等前缀
is_active = True
has_permission = False
can_edit = True

# ✅ 正确: 在类中
class User:
    def __init__(self) -> None:
        self.is_admin = False
        self.has_verified_email = False
```

### 避免的命名

```python
# ❌ 错误: 单字母变量（除了循环计数器）
def process(d):  # d 是什么？
    pass

# ✅ 正确: 使用描述性名称
def process(data: dict[str, Any]):
    pass

# ❌ 错误: 使用 Python 内置名称
list = [1, 2, 3]  # 覆盖了内置的 list
dict = {}         # 覆盖了内置的 dict

# ✅ 正确: 使用其他名称
items = [1, 2, 3]
data = {}
```

## 11. 异步 I/O 与并发

### 核心原则

- FastAPI 路由优先使用 `async def`，但**严禁**在 `async` 函数中调用阻塞 I/O
- 所有外部调用（HTTP、数据库、Redis、消息队列）必须使用异步客户端
- 不可避免的阻塞调用必须用 `asyncio.to_thread` 或线程池隔离
- CPU 密集型任务使用进程池（`ProcessPoolExecutor`），不要在事件循环中执行
- HTTP 客户端必须复用连接池，禁止每次请求创建新 client

### 阻塞调用的处理

```python
# ❌ 错误: async 函数中直接调用阻塞 I/O，会阻塞整个事件循环
import requests

@router.get("/weather")
async def get_weather(city: str) -> dict:
    response = requests.get(f"https://api.example.com/weather?city={city}")
    return response.json()

# ❌ 错误: async 函数中执行阻塞计算
@router.post("/hash")
async def compute_hash(data: bytes) -> str:
    return slow_hash_function(data)  # 阻塞 100ms+

# ✅ 正确: 使用异步 HTTP 客户端

@router.get("/weather")
async def get_weather(
    city: str,
    client: Annotated[httpx.AsyncClient, Depends(get_http_client)],
) -> dict:
    response = await client.get(
        "https://api.example.com/weather",
        params={"city": city},
    )
    response.raise_for_status()
    return response.json()

# ✅ 正确: 阻塞调用放入线程池

@router.post("/hash")
async def compute_hash(data: bytes) -> str:
    return await asyncio.to_thread(slow_hash_function, data)
```

### HTTP 客户端连接池

```python

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时创建连接池，关闭时释放。"""
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    try:
        yield
    finally:
        await app.state.http_client.aclose()
async def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client
```

### 并发执行多个异步任务

```python

# ✅ 正确: 并发执行独立任务
async def fetch_user_dashboard(user_id: int) -> Dashboard:
    profile, orders, messages = await asyncio.gather(
        fetch_profile(user_id),
        fetch_orders(user_id),
        fetch_messages(user_id),
    )
    return Dashboard(profile=profile, orders=orders, messages=messages)

# ✅ 正确: 限制并发数量，避免压垮下游
async def batch_fetch(user_ids: list[int]) -> list[User]:
    semaphore = asyncio.Semaphore(10)

    async def fetch_one(uid: int) -> User:
        async with semaphore:
            return await fetch_user(uid)

    return await asyncio.gather(*[fetch_one(uid) for uid in user_ids])

# ✅ 正确: 使用 TaskGroup（Python 3.11+），异常自动取消同组任务
async def process(user_id: int) -> None:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(send_email(user_id))
        tg.create_task(update_metrics(user_id))
```

### 同步与异步函数的选择

| 场景 | 路由签名 |
|------|---------|
| 路由内有 `await`（DB、HTTP、Redis 等） | `async def` |
| 路由内无 I/O，仅 CPU 计算 | `def`（FastAPI 自动放线程池） |
| 路由内有阻塞 I/O 且无法替换为异步库 | `def`（让 FastAPI 处理）或 `async def` + `to_thread` |

> ❗ 不要在 `async def` 路由里调用同步阻塞库（如 `requests`、`pymysql`、`time.sleep`）。

## 12. 统一错误响应

### 核心原则

- 所有 API 错误响应必须遵循统一结构（`code` / `message` / `detail`）
- 业务错误使用自定义异常 + 全局异常处理器，避免在路由中散写 `HTTPException`
- HTTP 状态码语义化：4xx 客户端错误，5xx 服务端错误
- 永远不要把内部异常堆栈、SQL 语句、敏感信息直接返回给客户端

### 统一响应模型

```python

class ErrorResponse(BaseModel):
    """统一错误响应。"""

    code: str = Field(description="业务错误码", examples=["USER_NOT_FOUND"])
    message: str = Field(description="可展示给用户的错误信息")
    detail: dict[str, Any] | None = Field(
        default=None,
        description="额外调试信息（生产环境可选择不返回）",
    )
```

### 业务异常基类

```python
class AppError(Exception):
    """业务异常基类。"""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "服务内部错误"

    def __init__(
        self,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.detail = detail
        super().__init__(self.message)
class UserNotFoundError(AppError):
    code = "USER_NOT_FOUND"
    status_code = 404
    message = "用户不存在"
```

### 全局异常处理器

```python

logger = logging.getLogger(__name__)
app = FastAPI()
@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.code,
            message=exc.message,
            detail=exc.detail,
        ).model_dump(exclude_none=True),
    )
@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            code="VALIDATION_FAILED",
            message="请求参数校验失败",
            detail={"errors": exc.errors()},
        ).model_dump(exclude_none=True),
    )
@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    # 未知异常：记录完整堆栈，但不泄露给客户端
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code="INTERNAL_ERROR",
            message="服务内部错误",
        ).model_dump(exclude_none=True),
    )
```

### 路由中的使用

```python
# ✅ 正确: 抛出业务异常，由全局处理器统一转换
@router.get("/user/{user_id}")
async def get_user(user_id: int, service: UserServiceDep) -> UserResponse:
    user = await service.get_user(user_id)
    if not user:
        raise UserNotFoundError(detail={"user_id": user_id})
    return UserResponse.model_validate(user)

# ❌ 错误: 在路由中直接构造响应字典
@router.get("/user/{user_id}")
async def get_user(user_id: int) -> dict:
    user = await find_user(user_id)
    if not user:
        return {"error": "not found"}  # 结构不统一
    return {"data": user}

# ❌ 错误: 直接抛 HTTPException 且无统一结构
raise HTTPException(status_code=404, detail="user not found")
```

### 错误码命名规范

- 全大写 + 下划线：`USER_NOT_FOUND`、`ORDER_ALREADY_PAID`
- 业务前缀分组：`AUTH_*`、`USER_*`、`ORDER_*`、`PAYMENT_*`
- 错误码与 HTTP 状态码解耦：错误码描述业务语义，HTTP 状态码描述协议层语义

## 13. 数据库与 Repository

### 核心原则

- 业务代码只能通过 Repository 访问数据库，禁止在 Service / 路由中直接写 SQL 或调用 ORM session
- 简单 CRUD / 简单只读路由可以通过依赖注入调用 Repository；涉及业务规则、跨 Repository 编排或事务边界时必须进入 Service
- **事务边界由 Service 层管理**，Repository 只负责单一数据操作，不开启事务
- 使用异步驱动（`asyncpg` + SQLAlchemy 2.0 async）
- 所有 schema 变更必须通过 Alembic 迁移，禁止 `create_all` 在生产环境运行
- Repository 返回领域模型或 ORM 实体，**不返回原始 Row / dict**

### 分层职责

| 层 | 职责 | 不应做 |
|----|------|--------|
| Repository | 单表 CRUD、查询封装、ORM ↔ 领域模型转换 | 开启/提交事务、调用其他 Repository |
| Service | 业务逻辑编排、跨 Repository 协调、事务边界 | 直接写 SQL、构造 Query 对象 |
| Router | 参数校验、调用 Service 或简单 Repository、组装响应 | 承载复杂业务逻辑、直接管理事务 |

### API 层直接调用 Repository 的边界

```python
# ✅ 可以接受: 简单读取，无业务规则、无事务编排
@router.get("/user/{user_id}")
async def get_user(user_id: int, repository: UserRepositoryDep) -> UserResponse:
    user = await repository.find_by_id(user_id)
    if not user:
        raise UserNotFoundError(detail={"user_id": user_id})
    return UserResponse.model_validate(user)
# ❌ 错误: 路由层直接管理事务和跨 Repository 编排
@router.post("/balance/transfer")
async def transfer_balance(request: TransferBalanceRequest) -> None:
    async with transaction() as session:
        users = UserRepository(session)
        orders = OrderRepository(session)
        ...
# ✅ 正确: 复杂流程进入 Service，由 Service 管理事务
@router.post("/balance/transfer")
async def transfer_balance(
    request: TransferBalanceRequest,
    service: UserServiceDep,
) -> None:
    await service.transfer_balance(
        from_user_id=request.from_user_id,
        to_user_id=request.to_user_id,
        amount=request.amount,
    )
```

### Session 与事务管理

```python

    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
engine = create_async_engine(
    SETTINGS.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=SETTINGS.DEBUG,
)

SessionFactory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)
@asynccontextmanager
async def transaction() -> AsyncIterator[AsyncSession]:
    """事务上下文：进入开启事务，正常退出 commit，异常 rollback。"""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Repository 实现

```python

class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, user_id: int) -> User | None:
        stmt = select(UserORM).where(UserORM.id == user_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return row.to_domain() if row else None

    async def save(self, user: User) -> User:
        orm = UserORM.from_domain(user)
        self._session.add(orm)
        await self._session.flush()  # 仅 flush，不 commit
        return orm.to_domain()
```

> ❗ Repository 内部只 `flush`，不 `commit`。事务边界由 Service 控制。

### Service 层管理事务

```python
class UserService:
    async def transfer_balance(
        self,
        from_user_id: int,
        to_user_id: int,
        amount: int,
    ) -> None:
        # ✅ 正确: Service 控制事务边界，跨 Repository 操作在同一事务中
        async with transaction() as session:
            users = UserRepository(session)
            orders = OrderRepository(session)

            sender = await users.find_by_id(from_user_id)
            receiver = await users.find_by_id(to_user_id)
            if not sender or not receiver:
                raise UserNotFoundError()

            sender.balance -= amount
            receiver.balance += amount

            await users.save(sender)
            await users.save(receiver)
            await orders.create_transfer_record(from_user_id, to_user_id, amount)
        # 退出 with 时自动 commit；异常自动 rollback
```
