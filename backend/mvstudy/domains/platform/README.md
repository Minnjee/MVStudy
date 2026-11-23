# 平台基础：身份、权限与班级名册（01 号票）

本域提供 U1 登录、U2 当前身份、U5 班级名册，并交付全平台共用的应用工厂、Alembic 迁移入口与幂等开发种子。U3/U4 归 10 号票，F1 归 11 号票，P1 归 32 号票。

## 前置条件

- PostgreSQL 16，已建 `mvstudy` 与 `mvstudy_test` 两个库，属主为业务账号 `mvstudy`
- Python 3.12 及以上
- 连接串只从 `DATABASE_URL` 读取，默认 `postgresql+psycopg://mvstudy:mvstudy@127.0.0.1:5433/mvstudy`

首次使用先复制配置模板：

```bash
cp .env.example .env      # 按本机端口、口令修改
```

## 建库与迁移

在**仓库根**执行（`alembic.ini` 与 `migrations/` 都在根上，业务域内不放迁移）：

```bash
python -m alembic upgrade head
python -m alembic heads          # 期望只有一个 head
python -m alembic check          # 期望模型与库结构无差异
```

全部建表只走 Alembic，应用启动与测试都不调用 `create_all()`。

## 开发种子

两个班、三类角色、十一个账号，可重复执行：

```bash
cd backend
python -m mvstudy.domains.platform.seed
```

| 账号 | 角色 | 班级 |
|---|---|---|
| `a01` / `Admin@123` | 管理员 | — |
| `t01` / `Teach@123` | 教师 | c1 |
| `t02` / `Teach@123` | 教师 | c2 |
| `s01`–`s04` / `Stud@123` | 学生 | c1 |
| `s05`–`s08` / `Stud@123` | 学生 | c2 |

`t01` 与 `t02` 各教一个班，用于检验"教师查他班得 404"。若一人带两班，该校验无法成立。

## 测试

票级集成测试走隔离库 `mvstudy_test`，**不允许**以 SQLite 替代：

```bash
python -m pytest tests/test_platform_integration.py -q
```

域内单元测试需要把 `backend` 放进 `PYTHONPATH`：

```bash
PYTHONPATH=backend python -m pytest backend/mvstudy/domains/platform -q
```

`unittest` 入口同样可用（团队旧基线沿用）：

```bash
python -m unittest discover -s tests
python -m unittest discover -s backend/mvstudy/domains/platform -t backend
```

结构约束检查（业务代码只在域目录、宿主不写路由、跨域只走公开入口）：

```bash
python tools/check_layout.py
```

测试通过 `alembic.command.upgrade(config, "head")` 在 `mvstudy_test` 上建表，因此测的是真实迁移产物，不是模型反射。

## 启动

```bash
cd backend
python -m flask --app mvstudy.app:create_app run --port 8000
```

前端 `vite.config.ts` 把 `/api` 代理到 `127.0.0.1:8000`，端口需一致。

## 手工验收

```bash
# U1 登录
curl -s -X POST http://127.0.0.1:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"login":"s01","password":"Stud@123"}'

# U2 取身份（TOKEN 换成上一步的 access_token）
curl -s http://127.0.0.1:8000/api/me -H "Authorization: Bearer TOKEN"

# 错误口令 → 401 invalid_credentials
curl -s -X POST http://127.0.0.1:8000/api/login \
  -H "Content-Type: application/json" -d '{"login":"s01","password":"wrong"}'

# 学生查他班名册 → 404 not_found（s01 属 c1，查 c2）
curl -s -o /dev/null -w "%{http_code}\n" \
  http://127.0.0.1:8000/api/classes/c2/members -H "Authorization: Bearer TOKEN"
```

错误响应统一为 `{"error":{"code":"…","message":"…"}}`。

## 给其他域的装配边界

**`g.current_actor`** 由宿主 `create_app()` 在每个请求注入，结构逐字等同 U2 响应：

```python
{
  "user_id": "u-s01",
  "display_name": "李同学",
  "role_id": "student",
  "permissions": ["case.read", "submission.write"],
  "classes": [{"class_id": "c1", "relation": "student"}],
}
```

未登录或凭证失效时为 `None`。8 号 `analytics/routes.py` 已按此结构读取，改动字段会直接破坏其调用。

**授权逐次查库。** JWT 只携带 `user_id`；`enabled`、角色权限与班级关系每次请求重新读取。因此停用账号或撤销权限后，旧凭证的下一个请求即失效，无需等待 token 过期。

**`create_review_demo()` 必须保留。** 它是 7 号评审的独立演示入口，被其测试引用。23 号票接入统一身份之前，正式 `create_app()` 不注册 review 蓝图。

**对外可复用的用例函数**（不经 HTTP 亦可直接调用，2/4/8/9 号按需使用）：

| 函数 | 位置 | 用途 |
|---|---|---|
| `login(session, login_name, password, secret, ttl_minutes)` | `identity.py` | 校验口令并签发凭证，失败抛 `AuthError` |
| `load_current_actor(session, user_id)` | `identity.py` | 组装 U2 结构；停用或不存在返回 `None` |
| `list_members(session, actor, class_id, relation)` | `classes.py` | 返回名册项；无权限返回 `None` |

## 本票边界

不含：用户启停与角色权限维护（U3/U4，10 号票）、文件上传下载（F1，11 号票）、三类首页指标（P1，32 号票）。前端图形界面的登录跳转与刷新恢复需人工点验，自动化只覆盖构建与接口。
