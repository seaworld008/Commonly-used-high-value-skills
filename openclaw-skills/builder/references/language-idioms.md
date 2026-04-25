# Language Idioms: TypeScript, Go, Python

> Per-language idiomatic patterns, project structure, type safety, error handling, and testing

## 1. TypeScript (6.0 / tsgo 7.0)

### Idioms

- `satisfies` operator: validates type conformance while preserving inferred type
- `as const` assertions: preserve literal types, replace runtime enums
- Template literal types for combinatorial string unions
- `using` / `await using` declarations (Explicit Resource Management) for deterministic cleanup of DB connections, file handles, HTTP clients
- ESM-first; barrel exports via `index.ts`

```typescript
// satisfies: type-safe config with preserved inference
const colors = { red: [255, 0, 0], green: "#00FF00" } satisfies Record<string, Color>;
colors.red.map(v => v * 2);  // OK: tuple type preserved (not Color)

// as const enum alternative (no runtime cost)
const Status = { Pending: "pending", Approved: "approved" } as const;
type Status = (typeof Status)[keyof typeof Status];

// Template literal types
type FullEndpoint = `${"GET" | "POST"} ${"/users" | "/posts"}`;
```

### Project Structure

- Feature-based directories (not type-based layers)
- Node.js backend: `"module": "NodeNext"`, `"moduleResolution": "NodeNext"`
- Frontend (bundler): `"module": "ESNext"`, `"moduleResolution": "Bundler"`

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "verbatimModuleSyntax": true
  }
}
```

### Type Safety

Branded types with Zod v4 (stable):

```typescript
// Zod v4: branded types
const UserIdSchema = z.uuid().brand<'UserId'>();  // v4: top-level z.uuid()
type UserId = z.infer<typeof UserIdSchema>;

// Zod v4: @zod/mini for tree-shaking
import { z, string, object } from '@zod/mini';

// Zod v4: built-in JSON Schema export + unified error field
const jsonSchema = UserSchema.toJSONSchema();
z.string({ error: 'Must be a string' });
```

Manual branded types / type guards:

```typescript
type Brand<T, B extends string> = T & { readonly __brand: B };
type UserId = Brand<string, "UserId">;
type OrderId = Brand<string, "OrderId">;
getUser(orderId);  // Compile error

// Exhaustiveness check
function getArea(shape: Shape): number {
    switch (shape) {
        case "circle": return Math.PI;
        case "square": return 1;
        default:
            const _exhaustive: never = shape;  // error when new Shape added
            return _exhaustive;
    }
}

// Type guard (prefer over `as` assertion)
function isUser(v: unknown): v is User {
    return typeof v === "object" && v !== null && "name" in v;
}
```

### Error Handling

- `neverthrow` `Result<T, E>` for domain errors; `throw` only for programming bugs
- `fromPromise` for async operations

```typescript
import { fromPromise } from 'neverthrow';

async function createUser(email: string): Promise<Result<User, DomainError>> {
    return fromPromise(db.insert({ email }), (e) => new DbError(e));
}
```

### Testing

```typescript
// Vitest + AAA pattern
describe("UserService", () => {
    it("creates user with valid email", async () => {
        const repo = { save: vi.fn().mockResolvedValue({ id: "1" }) };
        const result = await new UserService(repo).create({ email: "a@b.com" });
        expect(result.isOk()).toBe(true);
        expect(repo.save).toHaveBeenCalledOnce();
    });
});

// Type-level testing
expectTypeOf(parseId("123")).toEqualTypeOf<UserId>();

// MSW for API boundary mocking; testcontainers for integration
const container = await new PostgreSqlContainer().start();

// Property-based (fast-check)
fc.assert(fc.property(fc.array(fc.integer()), xs => sorted(xs).length === xs.length));
```

---

## 2. Go (1.22+)

### Idioms

- Accept interfaces, return structs
- `range` over int (1.22), range-over-func iterators (1.23), generic type aliases (1.24)
- Structured logging with `slog` (stdlib); `any` instead of `interface{}` (1.18+)

```go
// Go 1.22+: range over int
for i := range 10 { fmt.Println(i) }

// Go 1.23+: range-over-func iterators
func Filter[T any](s []T, fn func(T) bool) iter.Seq[T] {
    return func(yield func(T) bool) {
        for _, v := range s {
            if fn(v) && !yield(v) { return }
        }
    }
}

// Go 1.24: generic type aliases
type Set[T comparable] = map[T]struct{}
```

### Project Structure

```
myproject/
├── cmd/api/main.go          # entry point (wiring only)
├── internal/                 # Go-enforced private packages
│   ├── user/                 # feature-based (handler/service/repo)
│   └── product/
├── pkg/                      # public library (omit if not needed)
├── api/                      # OpenAPI/Protobuf definitions
└── go.mod
```

Hexagonal variant: `internal/domain/` → `application/` → `adapter/` (http/postgres/redis).

Rules: no `utils/`, `helpers/`, `common/`; prefer flat over deep; use `internal/` aggressively.

Functional options:

```go
type Option func(*Server)
func WithTimeout(d time.Duration) Option { return func(s *Server) { s.timeout = d } }
func NewServer(addr string, opts ...Option) *Server {
    s := &Server{addr: addr, timeout: 30 * time.Second}
    for _, opt := range opts { opt(s) }
    return s
}
```

### Type Safety

- Generics with type constraints for domain repositories
- Constructor injection with interfaces (not concrete types)

```go
type UserService struct {
    repo   UserRepository  // interface, not *PostgresRepo
    logger *slog.Logger
}
func NewUserService(repo UserRepository, logger *slog.Logger) *UserService {
    return &UserService{repo: repo, logger: logger}
}
```

### Error Handling

```go
var (
    ErrNotFound     = errors.New("not found")
    ErrUnauthorized = errors.New("unauthorized")
)

func GetUser(id string) (*User, error) {
    user, err := db.FindUser(id)
    if err != nil { return nil, fmt.Errorf("GetUser(%s): %w", id, err) }
    return user, nil
}

if errors.Is(err, ErrNotFound) { /* 404 */ }
var validErr *ValidationError
if errors.As(err, &validErr) { /* handle */ }
// errors.Join for multiple validation errors (Go 1.20+)
```

- `panic` only for initialization failures; `errgroup` for concurrent error aggregation

### Testing

```go
// Table-driven + t.Parallel()
func TestUserService_Create(t *testing.T) {
    tests := []struct{ name, email string; wantErr bool }{
        {"valid", "a@b.com", false},
        {"invalid", "invalid", true},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            t.Parallel()
            _, err := NewUserService(&mockRepo{}).Create(tt.email)
            if (err != nil) != tt.wantErr {
                t.Errorf("wantErr=%v, got %v", tt.wantErr, err)
            }
        })
    }
}
```

| Command | Purpose |
|---------|---------|
| `go test -race ./...` | Race condition detection (mandatory) |
| `go test -coverprofile=c.out` | Coverage |
| `go test -bench=. -benchmem` | Benchmarks |

- Mocks: interface-based manual mocks; `t.Helper()` for helpers; `httptest` for HTTP
- Integration: `testcontainers-go`; property-based: `testing/quick` / `gopter`

```go
container, _ := postgres.Run(ctx, "postgres:16")
connStr, _ := container.ConnectionString(ctx)
```

---

## 3. Python (3.12+)

### Idioms

- PEP 695 type parameter syntax (no `TypeVar` boilerplate)
- Structural pattern matching (`match`/`case`)
- `asyncio.TaskGroup` over `asyncio.gather` for structured concurrency
- `frozen @dataclass` for domain entities; Pydantic only at API boundaries

```python
# PEP 695: new generic syntax
class Stack[T]:
    def __init__(self) -> None: self._items: list[T] = []
    def push(self, item: T) -> None: self._items.append(item)
    def pop(self) -> T: return self._items.pop()

type Vector = list[float]

# TaskGroup: automatic cancellation on exception (prefer over gather)
async def process_batch(items: list[str]) -> list[str]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(process_item(item)) for item in items]
    return [t.result() for t in tasks]

# Semaphore for concurrency control
async def fetch_with_limit(client: httpx.AsyncClient, url: str) -> str:
    async with asyncio.Semaphore(10):
        return (await client.get(url)).text
```

### Project Structure

```
my-app/
├── pyproject.toml
├── uv.lock              # commit to VCS
├── .python-version
├── src/my_app/
│   ├── __init__.py
│   ├── py.typed         # PEP 561 (libraries)
│   └── main.py
└── tests/
    ├── conftest.py
    └── test_main.py
```

`uv` as default package manager (10x+ faster than pip):

```bash
uv init my-project && uv add fastapi pydantic
uv add --dev pytest ruff mypy && uv run pytest
```

`pyproject.toml` replaces `setup.py` + `requirements.txt`. Commit `uv.lock`; never use `pip install`.

Key `pyproject.toml` tool settings:
- `[tool.ruff.lint] select = ["E","W","F","UP","B","I","SIM","RUF"]`
- `[tool.mypy] python_version = "3.12", strict = true, plugins = ["pydantic.mypy"]`
- `[tool.pytest.ini_options] asyncio_mode = "auto"`

### Type Safety

Pydantic v2 at API boundaries; `frozen @dataclass` for domain entities:

```python
from pydantic import BaseModel, Field, model_validator
from typing import Annotated
from dataclasses import dataclass

# API boundary (Pydantic)
class CreateUserRequest(BaseModel):
    email: Annotated[str, Field(pattern=r'^[\w.-]+@[\w.-]+\.\w+$')]
    age: Annotated[int, Field(ge=0, le=150)]

# Domain entity (frozen dataclass, NOT BaseModel)
@dataclass(frozen=True)
class User:
    id: str
    email: str
    age: int
```

- mypy `--strict` in CI; pyright for IDE feedback
- `Protocol` for structural subtyping

```python
class Serializable(Protocol):
    def to_dict(self) -> dict[str, object]: ...

def save[T: Serializable](item: T) -> None:
    db.insert(item.to_dict())
```

### Error Handling

- Custom exception hierarchies for OOP-style domain errors
- `returns.Result` for functional pipelines (optional)
- `Pydantic ValidationError` at API boundaries → HTTP 422
- `ExceptionGroup` + `except*` for concurrent error aggregation (3.11+)

### Testing

```python
@pytest.mark.parametrize("input_val, expected", [
    ("hello", "HELLO"), ("", ""),
    pytest.param("mixed", "MIXED", id="mixed_case"),
])
def test_to_upper(input_val: str, expected: str):
    assert to_upper(input_val) == expected

# Async (asyncio_mode = "auto" removes @pytest.mark.asyncio)
async def test_fetch_user():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        assert (await client.get("/users/1")).status_code == 200

# Property-based (hypothesis)
@given(st.lists(st.integers()))
def test_sort_preserves_elements(xs: list[int]):
    assert Counter(sorted(xs)) == Counter(xs)

# Integration (testcontainers)
with PostgresContainer("postgres:16") as pg:
    engine = create_engine(pg.get_connection_url())
```

- Mocks: `unittest.mock` with `autospec=True`; `AsyncMock` for coroutines; `respx` for httpx
- Fixture scopes: `function` (default) / `module` / `session` (DB connections)

---

## 4. Cross-Language Principles

### Testing Trophy

```
    ╱ E2E ╲           few: critical user journeys
   ╱ Integration ╲    many: API/DB boundaries, component connections
  ╱ Unit ╲            moderate: pure functions, business logic
 ╱ Static Analysis ╲  always: type checkers, lint
```

### Mock Strategies

| Principle | Rule |
|-----------|------|
| Mock at boundaries only | External I/O, network, DB — not internal collaborators |
| Own your mocks | Wrap third-party libs; mock the wrapper |
| Test behavior, not implementation | Assert outputs/side-effects, not call order |

### Property-Based Testing

| Property | Example |
|----------|---------|
| Round-trip | `decode(encode(x)) == x` |
| Idempotency | `f(f(x)) == f(x)` |
| Element preservation | `Counter(sort(x)) == Counter(x)` |
| Invariants | `0 <= normalize(x) <= 1` |

| Language | Tool |
|----------|------|
| TypeScript | fast-check |
| Go | `testing/quick`, gopter |
| Python | hypothesis |

### Test Quality Targets

| Metric | Target |
|--------|--------|
| Branch coverage | 80%+ |
| Mutation score | 70%+ |
| Flaky rate | < 1% |
| Unit test speed | < 1s per test |

### Anti-Patterns (All Languages)

| # | Pattern | Fix |
|---|---------|-----|
| 1 | Inter-test dependencies | Fully isolate each test (no shared mutable state) |
| 2 | Testing implementation details | Test observable behavior |
| 3 | Excessive mocking | Complement with integration tests |
| 4 | `sleep` in tests | Use events / polling / testcontainers |
| 5 | Large snapshot assertions | Small, focused assertions |

---

**Sources:**
- [satisfies operator (2ality)](https://2ality.com/2025/02/satisfies-operator.html)
- [Total TypeScript Patterns](https://www.totaltypescript.com/four-essential-typescript-patterns)
- [TypeScript 5.8 Release](https://devblogs.microsoft.com/typescript/announcing-typescript-5-8/)
- [Go 1.24 Release Notes](https://go.dev/blog/go1.24)
- [Go Anti-patterns (hackmysql)](https://hackmysql.com/golang/go-antipatterns/)
- [ThreeDots Clean Architecture](https://threedots.tech/post/introducing-clean-architecture/)
- [Python 3.12 What's New](https://docs.python.org/3/whatsnew/3.12.html)
- [Real Python uv Guide](https://realpython.com/python-uv/)
- [Ruff Configuration](https://docs.astral.sh/ruff/configuration/)
- [Testing Trophy (Kent C. Dodds)](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications)
- [Property-Based Testing with Hypothesis](https://semaphore.io/blog/property-based-testing-python-hypothesis-pytest)
