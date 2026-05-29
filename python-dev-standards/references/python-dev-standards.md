<!-- Full reference for the python-dev-standards skill. -->

# Python Development Standards

## Standard Positioning

This standard guides AI in generating more maintainable, testable Python code. It serves as scaffolding and architectural constraints during project initialization, and as a refactoring checklist after coding to unify directory structure, configuration management, type annotations, exception handling, testing practices, and toolchain configuration.

Core goals:
- Ensure AI-generated code defaults to clear layering, stable boundaries, and consistent style
- Reduce common engineering issues such as hardcoding, implicit dependencies, exception swallowing, and blocking I/O
- Provide a unified basis during initialization, iterative development, code review, and subsequent refactoring

## 1. Project Architecture

### Standard Directory Structure

```
project_root/
├── src/
│   └── project_name/
│       ├── __init__.py        # Package init, exposes SRC_PATH, ROOT_PATH
│       ├── core/              # Core shared capabilities
│       │   ├── config.py
│       │   ├── http_client.py
│       │   ├── logging.py
│       │   └── observability.py
│       ├── api/               # FastAPI application entry
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── routes/
│       │   └── middleware/
│       ├── domain/            # Business domains (isolated by scenario)
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

### Root Package Path Constants

`src/project_name/__init__.py` serves as the root package initialization file and must embed project path constants for uniformly locating the `src` package directory and project root:

```python
import os

SRC_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT_PATH = os.path.dirname(os.path.dirname(SRC_PATH))
```

Conventions:
- `SRC_PATH` points to `src/project_name/`
- `ROOT_PATH` points to `project_root/`
- Other modules needing to locate project files import `ROOT_PATH` from the root package; do not recalculate the project root in each module
- `ROOT_PATH` is a string path; use `os.path.join(ROOT_PATH, "...")` for path concatenation

### Web Pages (Optional)

In pure backend mode, web pages can be served directly: add a `static/` directory at the project root for HTML / CSS / JS, served by FastAPI static hosting; pages call `/api/*` via fetch for dynamic interaction, optionally using lightweight libraries like htmx / Alpine.js. If server-side rendering is truly needed, introduce a template engine (Jinja2, Mako, etc.) — this standard does not prescribe one.

Minimal increment on top of the standard structure:

```
project_root/
├── src/project_name/...      # Follow the "Standard Directory Structure" above
├── static/                   # Web pages, sibling to src/
│   ├── index.html
│   ├── css/
│   └── js/
├── tests/
├── config/
└── ...
```

Mount (after all API routes are registered):

```python
app.mount("/", StaticFiles(directory=os.path.join(ROOT_PATH, "static"), html=True), name="web")
```

Conventions:
- Static resources go in `static/`, sibling to `src/`; no pre-defined subdirectories
- Pages only communicate with the backend via `/api/*`; do not directly access internal backend state
- For complex frontend interactions, switch to the separate frontend/backend variant

### Variant: Separate Frontend / Backend

For projects where the frontend is an independent SPA with independent deployment. The repository top level is divided into two projects, each maintaining its own standards:

```
project_root/
├── backend/         # Backend project, internally follows the "Standard Directory Structure"
├── frontend/        # Frontend project, structure determined by frontend standards, out of scope
└── README.md
```

Backend constraints:
- All routes must be under the `/api` prefix; breaking changes go through a new version prefix (e.g. `/api/v2`)
- Responses must be serialized with `*Response` schemas; returning ORM entities directly is prohibited
- CORS is only open in development; production serves through reverse proxy with same-origin deployment

### Selection Guidance

Default to the **standard directory structure**. Use the separate frontend/backend variant when the frontend is an independent SPA.

### Layer Responsibilities

#### core Layer (Shared Capabilities)
- Configuration management (`config.py`)
- HTTP client wrappers
- Logging configuration and observability
- LLM call wrappers (if applicable)
- General utility functions
- **Must not depend on business logic**

#### api Layer (Application Entry)
- Application initialization and lifecycle management
- Route registration
- Middleware configuration
- Global exception handling

#### domain Layer (Business Domains)
- `models.py`: Domain models (Pydantic Model or dataclass, chosen by data boundary)
- `service.py`: Business logic
- `repository.py`: Data access layer
- `schemas.py`: API request/response Pydantic Models

### Data Carrier Selection

Complex objects should be explicitly modeled; do not pass `dict[str, Any]` between layers for long.

- External boundary data uses Pydantic Model: FastAPI request/response, third-party API returns, config files, environment variables, message queue payloads, LLM structured output, etc.
- Internal trusted data may use `@dataclass(slots=True)`: domain objects, Service layer DTOs, algorithm intermediate results, temporary data structures, etc.
- When runtime validation, type coercion, default handling, error messages, JSON serialization, or OpenAPI integration are needed, use Pydantic Model.
- When only lightweight internal data carrying is needed and the data source is trusted, use dataclass.
- `dict` is only for temporary mapping, simple key-value collections, external raw JSON, or error `detail` in dynamic contexts.

### Core Principles

- ✅ **Must** use `src-layout` (code under `src/`)
- ✅ **Must** isolate submodules by business scenario; avoid single giant modules
- ✅ **Must** choose explicit carriers for complex objects: Pydantic Model for external boundaries, dataclass for internal trusted data
- ✅ **Allowed** API layer to access Repository via dependency injection in simple CRUD, simple read-only, dependency assembly, or composition root scenarios
- ✅ **Must** place business rules, transaction boundaries, cross-Repository orchestration, or cross-resource flows in the Service layer
- ✅ **Recommended** use dependency injection to manage inter-layer dependencies

### Example Code

#### Correct Layering Example

```python
class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def get_user(self, user_id: int) -> User | None:
        return await self._repository.find_by_id(user_id)


router = APIRouter()
async def get_user_service(session: AsyncSessionDep) -> UserService:
    # Dependency injection: session provided by request-level dependency; see "13. Database & Repository"
    return UserService(repository=UserRepository(session))

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

#### Not Recommended Example

```python
# ❌ Wrong: route layer carrying transactions and cross-Repository orchestration
@router.post("/balance/transfer")
async def transfer_balance(request: TransferBalanceRequest) -> None:
    async with transaction() as session:
        users = UserRepository(session)
        orders = OrderRepository(session)
        ...
```

## 2. Toolchain Configuration Templates

### Dependency & Environment Management (uv)

Unified use of [uv](https://docs.astral.sh/uv/) for virtual environment, dependency, and run entry management; do not mix pip / poetry / conda.

- Dependency declarations go in `pyproject.toml`: runtime deps under `[project].dependencies`, dev tools under `[dependency-groups].dev`
- `uv.lock` **must be committed** to ensure consistent installs across team and CI; do not edit lock files manually
- Common commands: `uv sync` (restore environment from lock), `uv add <pkg>` / `uv add --dev <pkg>` (add/remove deps and update lock), `uv run <cmd>` (execute within project environment, no manual activate needed)
- All toolchain commands (lint / typecheck / test) go through `uv run`, consistent with the Makefile and CI below

### pyproject.toml

The template below is for new projects, containing only generic project metadata, testing, ty, and Ruff configuration; business dependencies are added as needed. Existing projects should follow their current Python version and toolchain constraints; do not auto-upgrade just to match the template.

```toml
[project]
name = "project-name"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = "~>=3.14.0"
dependencies = []

[dependency-groups]
dev = [
    "ty>=0.0.34",
    "pytest>=9.0.0",
    "pytest-asyncio>=1.3.0",
    "ruff>=0.14.0",
]

[tool.pytest.ini_options]
testpaths = "tests"
asyncio_mode = "auto"
python_files = "tests.py test_*.py *_tests.py"
log_cli = true
log_cli_level = "DEBUG"
log_cli_format = "%(asctime)s %(levelname)s %(filename)s [line:%(lineno)d] - %(message)s"
log_cli_date_format = "%H:%M:%S"

[build-system]
build-backend = "hatchling.build"
requires = ["hatchling"]

[tool.ty.src]
include = ["src", "tests"]
exclude = [".git", ".venv", "__pycache__", "build", "dist"]

[tool.ty.environment]
python = "./.venv"
python-version = "3.14"

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

### Makefile

Unified command entry point; avoid team members memorizing different parameters.

```makefile
.PHONY: format lint typecheck test check

format:
	uv run ruff format src tests

lint:
	uv run ruff check --fix src tests

typecheck:
	uv run ty check

test:
	uv run pytest tests/

check: format lint typecheck test
```

### Pre-commit Checks

Before committing, **must** run the following checks and confirm all pass:

```bash
make check
```

Execution order:
1. `make format` — auto-format code
2. `make lint` — static analysis and style check
3. `make typecheck` — type check
4. `make test` — run tests

Checks that fail pre-commit must not be merged; CI should reuse the same command configuration.


## 3. Configuration Management

### Configuration File Structure

```
config/
└── .env.base       # Base default config (commit-able, no secrets)

.env.example        # Config template (must be committed)
.env                # Local override (do not commit)
```

### Configuration Priority (low to high)

1. `Settings` class field defaults
2. `config/.env.base` (base config)
3. Project root `.env` (local override)
4. System environment variables (highest priority)

### Environment Identifier

`ENV` is only a runtime environment identifier (e.g. `dev` / `fat` / `prod`), not used to load environment-specific config files from the repository. Environment differences are injected by the runtime platform via system environment variables; local development differences use the project root `.env` override.

### Configuration Class Definition

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

> Manually merging multiple env sources instead of using `pydantic-settings` built-in `env_file` is for precise control over the override order "`.env.base` < `.env` < system env vars" (built-in `env_file` priority for multiple files + `os.environ` is not intuitive enough). If the project only has a single env source, `SettingsConfigDict(env_file=...)` can be used directly for simplification.

### Usage

```python
# ✅ Correct: import global config
def connect_database():
    return create_engine(SETTINGS.DATABASE_URL)

if SETTINGS.DEBUG:
    print("Debug mode enabled")

# ❌ Wrong: hardcoded config
DATABASE_URL = "postgresql://localhost/mydb"

# ❌ Wrong: read environment variables directly
debug = os.getenv("DEBUG")  # should use SETTINGS.DEBUG
```

### Configuration File Examples

```bash
# config/.env.base (base config)
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# .env.example (config template, no real secrets)
DATABASE_URL=
REDIS_URL=
SECRET_KEY=

# .env (local override, do not commit)
DEBUG=true
DATABASE_URL=postgresql://localhost/mydb_dev
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-key-change-in-production
```

### Core Principles

- ✅ **Must** use `pydantic-settings` for configuration management
- ✅ **Must** provide `.env.example` documenting all required variables
- ❌ **Prohibited** committing project root `.env`
- ✅ **Must** inject production environment differences via system environment variables
- ❌ **Prohibited** hardcoding keys, tokens, or credentials
- ❌ **Prohibited** committing production environment secrets to version control
- ✅ **Recommended** use `Field` to add descriptions and validation rules

## 4. Testing Standards

### Core Principles

#### Unit Tests
- Test the behavior of a single function or method
- Must be repeatable, isolated, and fast
- Avoid network I/O, filesystem I/O, database access
- **Must not drop tables or business data**
- **Minimize mock usage**, prefer real implementations or lightweight substitutes

#### Integration Tests
- Test collaboration among multiple components
- May access databases, external APIs, filesystem
- Use test databases or containerized environments

### Unit Test Example

```python
# ✅ Correct: use lightweight substitute instead of mock
class FakeUserRepository:
    """Fake Repository for testing."""

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

> The template sets `asyncio_mode = "auto"`, so async test functions do not need `@pytest.mark.asyncio` individually; the example keeps the marker only for explicit illustration.

### Running Tests

```bash
# Test a specific file
uv run pytest tests/unit/test_user_service.py

# Run all unit tests
uv run pytest tests/unit/
```


## 5. FastAPI Development

### Core Principles

- Complete type annotations (new projects default to Python 3.14; existing projects follow their current Python version)
- Use Pydantic v2 for validation
- Use `Annotated` + `Depends` for dependency injection
- Prefer `async def`

### Route Naming Conventions

All business APIs must be mounted under the `/api` prefix. Route functions or `APIRouter` internals may only write object/action paths; the application entry adds the `/api` prefix uniformly.

**Format**: `/object/action` (object/action)
**Style**: all lowercase, kebab-case

```python
# ✅ Correct
@router.post("/user/create")    # external path: /api/user/create
@router.get("/order/list")      # external path: /api/order/list
@router.post("/image/enhance")  # external path: /api/image/enhance

# ❌ Wrong
@router.post("/create_user")
@router.get("/getOrders")
```

```python
app = FastAPI()
app.include_router(user.router, prefix="/api")
```

### Pydantic v2 Model Definition

```python
class UserCreate(BaseModel):
    """Create user request model."""

    username: Annotated[str, Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Username",
        examples=["john_doe"],
    )]
    email: Annotated[EmailStr, Field(
        description="Email address",
        examples=["alice@example.com"],
    )]
    password: Annotated[str, Field(
        min_length=8,
        max_length=128,
        description="Password",
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        return v
```

### Dependency Injection

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

### List Endpoints and Pagination

List / query endpoints must paginate; returning unlimited full datasets is prohibited. Use unified limit/offset pagination parameters and return a paginated response structure with total count, for frontend paginator rendering.

```python
class PageParams(BaseModel):
    limit: Annotated[int, Field(default=20, ge=1, le=100)]
    offset: Annotated[int, Field(default=0, ge=0)]

class Page[T](BaseModel):
    """Unified paginated response."""

    items: list[T]
    total: int
    limit: int
    offset: int

@router.get("/user/list")
async def list_users(
    page: Annotated[PageParams, Query()],
    service: UserServiceDep,
) -> Page[UserResponse]:
    users, total = await service.list_users(limit=page.limit, offset=page.offset)
    return Page(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )
```

Conventions:
- `limit` must have an upper bound (e.g. `le=100`) to prevent single-request full table pulls
- Repository / Service returns both current page data and `total`; do not perform secondary queries in the route layer
- For large datasets or stable pagination requirements, switch to cursor pagination (ordered key cursor) to avoid deep offset performance issues

## 6. Type Annotations

### Python Version Policy

New projects default to Python 3.14; existing projects follow the current Python version in `pyproject.toml`, ty configuration, and CI. Do not modify a project's Python version solely because of this standard unless the user explicitly requests an upgrade.

### Core Principles

- All public interfaces must have complete type annotations
- Use the latest Python type syntax supported by the target project
- Use `|` instead of `Union`
- Use `| None` instead of `Optional`

### Basic Type Annotations

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"

def calculate_total(prices: list[float], tax_rate: float = 0.1) -> float:
    subtotal = sum(prices)
    return subtotal * (1 + tax_rate)
```

### Union and Optional

```python
# ✅ Correct: use |
def normalize_identifier(value: str | int) -> str:
    ...

# ✅ Correct: use | None
def get_user(user_id: int) -> User | None:
    ...
```

### Generics (Python 3.12+)

```python
# ✅ Python 3.12+ syntax
def first[T](items: Sequence[T]) -> T | None:
    return items[0] if items else None

class Container[T]:
    def __init__(self, value: T) -> None:
        self.value = value

    def get(self) -> T:
        return self.value
```

### Avoiding Circular Imports

```python
if TYPE_CHECKING:
    from project_name.domain.user.repository import UserRepository

class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository
```

### Time and Timezones

Backend time uniformly uses timezone-aware UTC; store and internally pass in UTC, converting timezones only at the presentation layer when needed.

```python
# ❌ Wrong: naive datetime, no timezone info, breaks across timezones/serialization
created_at = datetime.now()
expired = datetime.utcnow()  # deprecated, still naive

# ✅ Correct: timezone-aware UTC
created_at = datetime.now(UTC)
```

Conventions:
- Prohibit `datetime.now()` / `datetime.utcnow()` and other naive forms; always use `datetime.now(UTC)`
- Database columns use `timestamptz` (timezone-aware), not naive timestamp
- When Pydantic receives `datetime` fields, reject timezone-less input or explicitly add UTC; do not silently treat as local time


## 7. Control Flow and Code Complexity

### Core Principles

1. Complex conditions should be split into semantically meaningful intermediate variables or private functions
2. When branching on the same state, command, event, or domain object, prefer `match/case` or lookup tables
3. Reserve `if` for range checks, multiple condition combinations, short-circuit evaluation needs, or conditions that are not the same dimension
4. Prohibit using `assert` for condition checks in `src` paths (only for test code)

### Prohibit assert for Condition Checks in src Paths

```python
# ❌ Wrong: using assert in src path (skipped by python -O)
def process_user_input(data):
    assert data is not None  # Prohibited! Skipped in production
    return data.upper()

# ✅ Correct: explicit check in business code
def process_user_input(data):
    if data is None:
        raise ValueError("Data cannot be None")
    return data.upper()

# ✅ Correct: using assert in test code
# tests/test_service.py
def test_process_user_input():
    result = process_user_input("hello")
    assert result == "HELLO"  # Allowed in tests
```

### Prefer match/case or Lookup Tables for Multi-branch Logic

`match/case` suits structured branching on the same object (field binding, type guards, multi-value union); lookup tables suit "enum/string → handler function" pure dispatch scenarios.

Common patterns (one example per line is sufficient):

- Literal / enum: `case "paid":`, `case OrderStatus.PAID:`
- Multi-value union: `case EventType.MESSAGE | EventType.ALERT:`
- Field binding: `case SseEvent(event=EventType.FAQ, data=data):`
- Guard condition: `case ... if isinstance(data, ChatObjectChunk):`
- Default branch: `case _:`

```python
# ✅ match/case: field binding + type guard + multi-value union
match event:
    case SseEvent(event=EventType.INTERRUPT):
        mark_interrupted()
    case SseEvent(event=EventType.FAQ, data=data) if isinstance(data, ChatObjectChunk):
        handle_faq(data)
    case SseEvent(event=EventType.MESSAGE_ALL | EventType.ALERT, data=data):
        handle_message(data)
    case _:
        handle_unknown(event)

# ✅ Lookup table: pure dispatch, avoiding long if/elif
HANDLERS = {
    OrderStatus.PAID: handle_paid,
    OrderStatus.REFUNDED: handle_refunded,
}
HANDLERS.get(order.status, handle_default)(order)
```

Constraints: branches match in order, specific patterns first; only use `|` when handling logic is identical; `if` guards only supplement extra conditions for the current pattern, do not stuff complex business logic; if a branch body exceeds a few lines, extract a private function; do not use bare variable names to match constants (`case PAID:` becomes capture, use `OrderStatus.PAID`); must explicitly handle unknown branches.

## 8. Exception Handling

### Core Principles

1. Use built-in exception classes
2. Custom exceptions inherit from existing exceptions, class names end with `Error`
3. Prohibit bare catches (`except:`), prohibit swallowing broad exceptions
4. Minimize try blocks

### Catch Specific Exceptions

```python
# ✅ Correct: catch specific exceptions, minimize try block
try:
    value = dictionary[key]
except KeyError:
    logger.warning(f"Key {key} not found")
    value = default_value

# ✅ Correct: catch multiple specific exceptions
try:
    result = int(user_input)
except (ValueError, TypeError) as e:
    logger.error(f"Invalid input: {e}")
    result = 0

# ❌ Wrong: bare catch, swallows KeyboardInterrupt
try:
    do_something()
except:
    pass

# ❌ Wrong: catches Exception but does not log, wrap, or re-raise
try:
    do_something()
except Exception:
    pass  # Swallows all exceptions
```

### Allowed Scenarios for Broad Exceptions

The following boundary scenarios allow catching `Exception`, but must log, wrap, or re-raise:

- Global exception handler: log full stack trace, return unified error response
- Transaction context: rollback on exception, then re-raise
- Task entry or background task boundaries: log failure reason, avoid silent task exit
- Wrapping third-party library exceptions: convert to project-internal exceptions, use `raise ... from e` to preserve original exception chain

### Custom Exceptions

```python
# ✅ Correct: custom exceptions
class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""

class UserNotFoundError(Exception):
    """Raised when user does not exist."""

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")

class ValidationError(ValueError):
    """Raised when data validation fails."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"{field}: {message}")
```

### Re-raising Exceptions

```python
# ✅ Correct: can catch broad exceptions when re-raising
try:
    process_data()
except Exception as e:
    logger.exception("Processing failed")
    raise  # Must re-raise

# ✅ Correct: wrap exceptions
try:
    connect_to_database()
except ConnectionError as e:
    raise DatabaseConnectionError("Failed to connect") from e
```

### Minimize try Blocks

```python
# ❌ Wrong: try block too large
try:
    user = get_user(user_id)
    validate_user(user)
    process_user(user)
    save_user(user)
    send_notification(user)
except Exception as e:
    logger.error(f"Error: {e}")

# ✅ Correct: only wrap operations that may fail
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

### Context Managers

```python
# ✅ Correct: use with for automatic resource handling
with open("file.txt") as f:
    content = f.read()

# ✅ Correct: custom context manager
@contextmanager
def database_transaction():
    """Database transaction context manager."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Usage
with database_transaction() as conn:
    conn.execute("INSERT INTO users ...")
```


## 9. Import Standards

### Core Principles

- Use `import x` to import packages and modules
- Use `from x import y`, where `x` is the package prefix and `y` is the module name
- Prohibit relative imports
- Prohibit wildcard imports
- Use full package paths

### Correct Import Styles

```python
# ✅ Correct: import module
from sound.effects import echo
echo.echofilter(...)

# ✅ Correct: use alias to resolve conflicts or shorten names
from absl import flags as absl_flags
from my_project.models import User as ProjectUser

# ✅ Correct: typing module exception, types can be imported directly
from typing import Any
from collections.abc import Mapping, Sequence

# ✅ Correct: use full package path
from my_project.database import connection
from my_project.models.user import User
```

### Incorrect Import Styles

```python
# ❌ Wrong: relative imports
from ..models import User
from . import utils

# ❌ Wrong: wildcard imports
from my_module import *

# ❌ Wrong: assuming module is in current directory
import models
from user import User
```

### Import Order

Organize imports in the following order, with a blank line between each group:

1. Standard library imports
2. Third-party library imports
3. Local application/library imports

```python
# ✅ Correct: import order
import os
import sys
from pathlib import Path

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from my_project.core.config import SETTINGS
from my_project.domain.user.models import User
```

### Avoiding Circular Imports

```python
# ✅ Correct: use TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from my_project.domain.user.repository import UserRepository

class UserService:
    def __init__(self, repository: UserRepository) -> None:
        # Type annotations are lazily evaluated, not imported at runtime
        self._repository = repository
```

### Conditional Imports

```python
# ✅ Correct: conditional import for optional dependencies
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

## 10. Naming Conventions

### Naming Style Overview

| Type | Style | Example |
|------|-------|---------|
| File names | `snake_case` | `my_module.py` |
| Package names | `lowercase` | `mypackage` |
| Class names | `PascalCase` | `MyClass` |
| Exceptions | `PascalCase` + Error | `MyError` |
| Functions / methods | `snake_case` | `my_function` |
| Variables | `snake_case` | `my_variable` |
| Constants | `UPPER_CASE` | `MY_CONSTANT` |
| Private members | `_snake_case` | `_private_var` |

### Class Naming

```python
# ✅ Correct: class names use PascalCase
class UserService:
    pass

class DatabaseConnection:
    pass

class HTTPClient:
    pass

# ✅ Correct: exception classes end with Error
class ValidationError(Exception):
    pass

class DatabaseConnectionError(Exception):
    pass
```

### Function and Variable Naming

```python
# ✅ Correct: functions and variables use snake_case
def calculate_total_price(items: list[Item]) -> float:
    total_price = 0.0
    for item in items:
        total_price += item.price
    return total_price

# ✅ Correct: private functions and variables use _snake_case
def _internal_helper(data: str) -> str:
    return data.upper()

class MyClass:
    def __init__(self) -> None:
        self._private_var = 0
```

> Single underscore `_x` is a convention for "internal use" (not enforced access restriction); double underscore `__x` triggers name mangling, only use when truly needed to avoid subclass attribute naming conflicts; for ordinary private members always use single underscore, do not abuse `__`.

### Constant Naming

```python
# ✅ Correct: constants use UPPER_CASE
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.example.com"

# ✅ Correct: private constants
_DEFAULT_BUFFER_SIZE = 1024
```

### FastAPI Route Naming

See [5. FastAPI Development - Route Naming Conventions](#route-naming-conventions).

### Pydantic Model Naming

```python
# ✅ Correct: request models end with an action
class UserCreate(BaseModel):
    """Create user request."""
    pass

class UserUpdate(BaseModel):
    """Update user request."""
    pass

class OrderQuery(BaseModel):
    """Order query parameters."""
    pass

# ✅ Correct: response models end with Response or Item
class UserResponse(BaseModel):
    """User response."""
    pass

class UserItem(BaseModel):
    """User list item."""
    pass

# ✅ Correct: general models use noun directly
class User(BaseModel):
    """User model."""
    pass
```

### File Naming

```python
# ✅ Correct: file names use snake_case
user_service.py
database_connection.py
http_client.py

# ❌ Wrong
UserService.py
databaseConnection.py
HTTPClient.py
```

### Package Naming

```
# ✅ Correct: package names use lowercase
myproject/
    core/
    domain/
    utils/

# ❌ Wrong
MyProject/
    Core/
    Domain/
```

### Boolean Variable Naming

```python
# ✅ Correct: use is_, has_, can_ prefixes
is_active = True
has_permission = False
can_edit = True

# ✅ Correct: in classes
class User:
    def __init__(self) -> None:
        self.is_admin = False
        self.has_verified_email = False
```

### Names to Avoid

```python
# ❌ Wrong: single-letter variables (except loop counters)
def process(d):  # What is d?
    pass

# ✅ Correct: use descriptive names
def process(user_payload: UserPayload) -> None:
    pass

# ❌ Wrong: using Python built-in names
list = [1, 2, 3]  # shadows built-in list
dict = {}         # shadows built-in dict

# ✅ Correct: use other names
items = [1, 2, 3]
data = {}
```


## 11. Async I/O and Concurrency

### Core Principles

- FastAPI routes prefer `async def`, but **strictly prohibited** from calling blocking I/O inside `async` functions
- All external calls (HTTP, database, Redis, message queue) must use async clients
- Unavoidable blocking calls must be isolated with `asyncio.to_thread` or a thread pool
- CPU-intensive tasks use process pool (`ProcessPoolExecutor`), do not execute in the event loop
- HTTP clients must reuse connection pools; creating a new client per request is prohibited

### Handling Blocking Calls

```python
# ❌ Wrong: directly calling blocking I/O in async function, blocks entire event loop
import requests

@router.get("/weather")
async def get_weather(city: str) -> dict:
    response = requests.get(f"https://api.example.com/weather?city={city}")
    return response.json()

# ❌ Wrong: executing blocking computation in async function
@router.post("/hash")
async def compute_hash(data: bytes) -> str:
    return slow_hash_function(data)  # blocks for 100ms+

# ✅ Correct: use async HTTP client
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

# ✅ Correct: put blocking calls in thread pool
@router.post("/hash")
async def compute_hash(data: bytes) -> str:
    return await asyncio.to_thread(slow_hash_function, data)
```

### HTTP Client Connection Pool

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: create connection pool on startup, release on shutdown."""
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

### Concurrent Execution of Multiple Async Tasks

```python
# ✅ Correct: execute independent tasks concurrently
async def fetch_user_dashboard(user_id: int) -> Dashboard:
    profile, orders, messages = await asyncio.gather(
        fetch_profile(user_id),
        fetch_orders(user_id),
        fetch_messages(user_id),
    )
    return Dashboard(profile=profile, orders=orders, messages=messages)

# ✅ Correct: limit concurrency to avoid overwhelming downstream
async def batch_fetch(user_ids: list[int]) -> list[User]:
    semaphore = asyncio.Semaphore(10)

    async def fetch_one(uid: int) -> User:
        async with semaphore:
            return await fetch_user(uid)

    return await asyncio.gather(*[fetch_one(uid) for uid in user_ids])

# ✅ Correct: use TaskGroup (Python 3.11+), exceptions auto-cancel sibling tasks
async def process(user_id: int) -> None:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(send_email(user_id))
        tg.create_task(update_metrics(user_id))
```

### Choosing Between Sync and Async Functions

| Scenario | Route Signature |
|----------|-----------------|
| Route has `await` (DB, HTTP, Redis, etc.) | `async def` |
| Route has no I/O, only CPU computation | `def` (FastAPI auto-places in thread pool) |
| Route has blocking I/O that cannot be replaced with async library | `def` (let FastAPI handle) or `async def` + `to_thread` |

> ❗ Do not call synchronous blocking libraries (e.g. `requests`, `pymysql`, `time.sleep`) inside `async def` routes.

## 12. Unified Error Responses

### Core Principles

- All API error responses must follow a unified structure (`code` / `message` / `detail`)
- Business errors use custom exceptions + global exception handlers; avoid scattering `HTTPException` in routes
- HTTP status codes are semantic: 4xx client errors, 5xx server errors
- Never return internal exception stack traces, SQL statements, or sensitive information directly to clients

### Unified Response Model

```python
class ErrorResponse(BaseModel):
    """Unified error response."""

    code: str = Field(description="Business error code", examples=["USER_NOT_FOUND"])
    message: str = Field(description="User-facing error message")
    detail: dict[str, Any] | None = Field(
        default=None,
        description="Additional debug info JSON object (only dynamic context, no complex business objects)",
    )
```

> Using `dict[str, Any]` for `detail` is an explicit exception allowed by Chapter 1 "Data Carrier Selection": error response additional context is dynamic key-value, not a business object that needs modeling.

### Business Exception Base Class

```python
class AppError(Exception):
    """Business exception base class."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "Internal server error"

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
    message = "User not found"
```

### Global Exception Handlers

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
            message="Request parameter validation failed",
            detail={"errors": exc.errors()},
        ).model_dump(exclude_none=True),
    )

@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    # Unknown exceptions: log full stack trace, but do not leak to client
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code="INTERNAL_ERROR",
            message="Internal server error",
        ).model_dump(exclude_none=True),
    )
```

### Usage in Routes

```python
# ✅ Correct: raise business exceptions, converted uniformly by global handler
@router.get("/user/{user_id}")
async def get_user(user_id: int, service: UserServiceDep) -> UserResponse:
    user = await service.get_user(user_id)
    if not user:
        raise UserNotFoundError(detail={"user_id": user_id})
    return UserResponse.model_validate(user)

# ❌ Wrong: directly constructing response dict in route
@router.get("/user/{user_id}")
async def get_user(user_id: int) -> dict:
    user = await find_user(user_id)
    if not user:
        return {"error": "not found"}  # structure not unified
    return {"data": user}

# ❌ Wrong: directly throwing HTTPException without unified structure
raise HTTPException(status_code=404, detail="user not found")
```

### Error Code Naming Conventions

- ALL_CAPS + underscores: `USER_NOT_FOUND`, `ORDER_ALREADY_PAID`
- Business prefix grouping: `AUTH_*`, `USER_*`, `ORDER_*`, `PAYMENT_*`
- Error codes are decoupled from HTTP status codes: error codes describe business semantics, HTTP status codes describe protocol-layer semantics


## 13. Database and Repository

### Core Principles

- Business code may only access the database through Repository; writing SQL or calling ORM session directly in Service / routes is prohibited
- Simple CRUD / simple read-only routes may call Repository via dependency injection; when business rules, cross-Repository orchestration, or transaction boundaries are involved, it must go through Service
- **Transaction boundaries are managed by the Service layer**; Repository is only responsible for single data operations and does not open transactions
- Use async drivers (`asyncpg` + SQLAlchemy 2.0 async)
- Repository returns domain models or ORM entities; **do not return raw Row / dict**

### Layer Responsibilities

| Layer | Responsibilities | Should Not Do |
|-------|-----------------|---------------|
| Repository | Single-table CRUD, query encapsulation, ORM ↔ domain model conversion | Open/commit transactions, call other Repositories |
| Service | Business logic orchestration, cross-Repository coordination, transaction boundaries | Write SQL directly, construct Query objects |
| Router | Parameter validation, call Service or simple Repository, assemble response | Carry complex business logic, manage transactions directly |

### Boundary for API Layer Directly Calling Repository

```python
# ✅ Acceptable: simple read, no business rules, no transaction orchestration
@router.get("/user/{user_id}")
async def get_user(user_id: int, repository: UserRepositoryDep) -> UserResponse:
    user = await repository.find_by_id(user_id)
    if not user:
        raise UserNotFoundError(detail={"user_id": user_id})
    return UserResponse.model_validate(user)

# ❌ Wrong: route layer directly manages transactions and cross-Repository orchestration
@router.post("/balance/transfer")
async def transfer_balance(request: TransferBalanceRequest) -> None:
    async with transaction() as session:
        users = UserRepository(session)
        orders = OrderRepository(session)
        ...

# ✅ Correct: complex flow enters Service, Service manages transactions
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

### Session and Transaction Management

```python
from sqlalchemy.ext.asyncio import (
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
    """Transaction context: enters and opens transaction, commits on normal exit, rollback on exception."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Request-level Session Dependency Injection

Simple read-only / simple CRUD routes obtain request-level session through FastAPI dependency injection; complex flows enter Service, and Service uses the `transaction()` above to explicitly manage transaction boundaries.

```python
async def get_session() -> AsyncIterator[AsyncSession]:
    """Request-level session: commits on normal exit, rollback on exception."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]

async def get_user_repository(session: AsyncSessionDep) -> UserRepository:
    return UserRepository(session)

UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
```

Conventions:
- `AsyncSessionDep` / `UserRepositoryDep` are reused by routes and `get_*_service` dependency assembly; do not repeatedly construct them everywhere
- `get_session` already commits transactions at the request boundary; Repository internals only `flush`, do not `commit`
- When Service needs to put multiple Repositories into the **same transaction**, it uses `transaction()` to manage its own session, not reusing the request-level session

### Repository Implementation

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
        await self._session.flush()  # only flush, do not commit
        return orm.to_domain()
```

> ❗ Repository internals only `flush`, do not `commit`. Transaction boundaries are controlled by Service.

### Service Layer Transaction Management

```python
class UserService:
    async def transfer_balance(
        self,
        from_user_id: int,
        to_user_id: int,
        amount: int,
    ) -> None:
        # ✅ Correct: Service controls transaction boundary, cross-Repository operations within same transaction
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
        # auto-commit on with exit; auto-rollback on exception
```

## 14. Logging and Observability

### Core Principles

- Use standard `logging`, each module gets `logger = logging.getLogger(__name__)`; using `print` for runtime info is prohibited
- Logging configuration is centralized in `core/logging.py`, initialized once at application startup (lifespan); do not call `basicConfig` in individual business modules
- Production outputs structured logs (JSON) for easy collection and querying; local development may use readable formats
- Control verbosity through log levels (`DEBUG`/`INFO`/`WARNING`/`ERROR`), driven by `SETTINGS.LOG_LEVEL`
- Exceptions use `logger.exception(...)` to record full stack trace (only at the catch point); do not print the same exception at every layer

### Logging Initialization

```python
def setup_logging() -> None:
    """Called once at application startup, level controlled by SETTINGS.LOG_LEVEL."""
    logging.basicConfig(
        level=SETTINGS.LOG_LEVEL.upper(),
        format="%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] - %(message)s",
    )

logger = logging.getLogger(__name__)
```

### Usage

```python
# ✅ Correct: module-level logger + parameterized logs, lazy formatting
logger.info("user created: user_id=%s", user.id)

# ✅ Correct: record stack trace at catch point
try:
    await charge(order)
except PaymentError:
    logger.exception("charge failed: order_id=%s", order.id)
    raise

# ❌ Wrong: print output / f-string eager formatting / logging sensitive fields
print("user created", user)
logger.info(f"login: token={token}")  # leaks credential, and formats regardless of level
```

### Prohibited Log Content

- Passwords, tokens, keys, Authorization headers, full ID / bank card numbers, and other sensitive data
- Full request/response bodies (may contain sensitive fields); when needed only log necessary fields and mask them
- Large objects in high-frequency paths, to avoid excessive log volume and performance degradation

### Observability (As Needed)

When tracing and metrics are needed, centralize integration in `core/observability.py` (e.g. OpenTelemetry): inject trace-id / request-id into request chains and output with logs, instrument external calls (HTTP, DB). Smaller projects may keep only structured logs + request-id without mandating a full APM.
