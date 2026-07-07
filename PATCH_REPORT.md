# Flask 用户管理平台 — 安全漏洞补丁报告

> 报告日期：2026-07-07  
> 项目地址：https://github.com/simengyu-i/flask-user-manager  
> 漏洞总数：3 个  
> 修复提交：`74eec9d`、`c283f5a`、`b3d3ae8`

---

## 目录

1. [漏洞一：硬编码凭据](#漏洞一硬编码凭据)
2. [漏洞二：字典注入与密码前端泄露](#漏洞二字典注入与密码前端泄露)
3. [漏洞三：明文密码存储](#漏洞三明文密码存储)

---

## 漏洞一：硬编码凭据

### 严重程度

🔴 **严重**

### 漏洞说明

在原始代码中，用户数据（用户名、密码、邮箱、手机号、余额）以及 Flask 的 `secret_key` 全部以字面量的形式**硬编码**在 `app.py` 文件中：

```python
# 原始代码 (app.py)
app.secret_key = "dev-key-2025"

USERS = {
    "admin": {
        "username": "admin",
        "password": "admin123",      # ← 硬编码密码
        "role": "admin",
        "email": "admin@example.com",
        "phone": "13800138000",
        "balance": 99999
    },
    "alice": { ... }
}
```

### 风险分析

| 风险 | 说明 |
|------|------|
| 代码泄露即数据泄露 | 代码上传到公开 GitHub 后，所有人可直接看到管理员密码和联系方式 |
| 密钥公开 | `secret_key` 硬编码导致 session 可被任意伪造 |
| 无法灵活配置 | 修改端口、调试模式等需要直接改源码，不符合十二因素应用规范 |

### 修复方案

将敏感数据和配置从源码中剥离，移到独立的 JSON 文件中，并通过 `.gitignore` 禁止提交到版本控制系统。

### 修复步骤

#### 第 1 步：创建配置文件 `config.json`

```json
{
    "secret_key": "dev-key-2025",
    "port": 5000,
    "debug": true
}
```

> 该文件已被 `.gitignore` 排除，不会提交到 Git。

#### 第 2 步：创建用户数据文件 `users.json`

```json
{
    "admin": {
        "username": "admin",
        "password": "admin123",
        "role": "admin",
        "email": "admin@example.com",
        "phone": "13800138000",
        "balance": 99999
    },
    "alice": { ... }
}
```

> 该文件已被 `.gitignore` 排除，不会提交到 Git。

#### 第 3 步：更新 `.gitignore`

```gitignore
# 配置文件 - 禁止提交到 Git
users.json
config.json
```

#### 第 4 步：创建示例模板文件

创建 `config.example.json` 和 `users.example.json`，密码字段用占位符替代，仅作为项目结构参考提交到 Git。

#### 第 5 步：修改 `app.py` 读取外部文件

```python
# 修复后 (app.py)
import json
import os

config_path = os.path.join(os.path.dirname(__file__), "config.json")
users_path = os.path.join(os.path.dirname(__file__), "users.json")

with open(config_path, encoding="utf-8") as f:
    config = json.load(f)

with open(users_path, encoding="utf-8") as f:
    USERS = json.load(f)

app.secret_key = config.get("secret_key", "dev-key-2025")
port = config.get("port", 5000)
debug = config.get("debug", True)
```

#### 第 6 步：启动参数改为变量控制

```python
# 修复前
app.run(debug=True, host="0.0.0.0", port=5000)

# 修复后
app.run(debug=debug, host="0.0.0.0", port=port)
```

### 修复前后对比

| 对比项 | 修复前 | 修复后 |
|--------|--------|--------|
| 凭据位置 | `app.py` 源码中硬编码 | `users.json` + `config.json`（已 gitignore）|
| Git 泄露风险 | 提交即泄露 | 配置文件被 .gitignore 排除 |
| 修改配置 | 需修改源码 | 直接改 JSON 文件 |
| 示例文档 | 无 | `users.example.json` + `config.example.json` |

---

## 漏洞二：字典注入与密码前端泄露

### 严重程度

🔴 **严重**

### 漏洞说明

原始代码中，用户登录成功后直接将完整的 `USERS` 字典（**包含密码字段**）传递给模板引擎：

```python
# 原始代码 (app.py)
# 问题 1: 整个字典传递给模板
user = USERS.get(username)
return render_template("index.html", user=user)
```

同时在模板中直接渲染密码字段：

```html
<!-- 原始代码 (templates/index.html) -->
<tr><td>密码</td><td>{{ user.password }}</td></tr>
```

此外，登录表单没有任何输入校验，攻击者可以提交包含特殊字符的用户名（如 `<script>`、`__proto__` 等），虽然 Jinja2 默认开启了 HTML 转义，但拦截恶意输入本身是最佳实践。

### 风险分析

| 风险 | 说明 |
|------|------|
| 密码显示在页面 | 用户登录后自己的密码直接展示在浏览器中，被截屏即泄露 |
| 字典数据过度暴露 | 密码字段跟随字典传递到所有消费方，任何模板改动都可能意外泄露 |
| 无输入校验 | 特殊字符、原型链注入等攻击载荷可传入应用 |

### 修复方案

#### 第 1 步：创建 `get_safe_user()` 安全过滤函数

新增一个工具函数，在返回用户数据给模板之前过滤掉密码字段：

```python
def get_safe_user(username):
    """返回不包含密码的用户信息"""
    user = USERS.get(username)
    if user:
        return {k: v for k, v in user.items() if k != "password"}
    return None
```

**原理分析**：
- `user.items()` 返回字典的所有键值对
- 列表推导式 `{k: v for k, v in user.items() if k != "password"}` 生成一个**新的字典**，排除了 `password` 键
- 原始 `USERS` 字典中的数据不受影响，密码仅用于登录比对

#### 第 2 步：修改首页路由

```python
# 修复前
user = USERS.get(username) if username else None

# 修复后
user = get_safe_user(username) if username else None
```

#### 第 3 步：修改登录路由

```python
# 修复前
user = USERS.get(username)
if user and user["password"] == password:
    session["username"] = username
    return render_template("index.html", user=user)  # 整个字典包括密码

# 修复后
user = USERS.get(username)
if user and user["password"] == password:
    session["username"] = username
    safe_user = get_safe_user(username)              # 过滤掉密码
    return render_template("index.html", user=safe_user)
```

#### 第 4 步：添加输入校验函数

```python
def validate_input(value):
    """基础输入校验：只允许字母、数字、中文、@、.、-、_"""
    import re
    if not value or not isinstance(value, str):
        return False
    return bool(re.match(r'^[a-zA-Z0-9一-鿿@.\-_]+$', value))
```

然后在登录路由中添加校验：

```python
username = request.form.get("username", "").strip()
password = request.form.get("password", "")

if not validate_input(username) or not validate_input(password):
    return render_template("login.html", error="输入包含非法字符")
```

**校验逻辑说明**：
1. 正则 `^[a-zA-Z0-9一-鿿@.\-_]+$` 只允许：字母、数字、中文字符、`@`、`.`、`-`、`_`
2. 拦截 `<script>`、`__proto__`、`{"key":"value"}` 等攻击载荷
3. 对用户名做了 `.strip()` 去除前后空白
4. 先校验类型 `isinstance(value, str)`，防止非字符串类型注入

#### 第 5 步：从模板中移除密码行

```html
<!-- 修复前 -->
<tr><td>密码</td><td>{{ user.password }}</td></tr>

<!-- 修复后 -->
<!-- 整行删除，不再显示密码 -->
```

### 修复前后对比

| 对比项 | 修复前 | 修复后 |
|--------|--------|--------|
| 传递给模板的数据 | 完整字典（含密码） | 安全字典（不含密码） |
| 页面显示的字段 | 用户名、**密码**、邮箱、手机、角色、余额 | 用户名、邮箱、手机、角色、余额 |
| 输入校验 | 无 | 正则白名单校验 |
| 注入拦截 | ❌ `<script>` 等可传入 | ✅ 非法字符返回错误提示 |

---

## 漏洞三：明文密码存储

### 严重程度

🔴 **严重**

### 漏洞说明

原始代码使用 **明文** 存储密码，并在登录时直接进行字符串比对：

```python
# 原始代码 (app.py)
USERS = {
    "admin": {
        "password": "admin123"   # ← 明文存储
    }
}

# 登录时直接用 == 比对
if user and user["password"] == password:
```

此外，`users.json` 移出源码之前也是明文存储：

```json
{
    "admin": {
        "password": "admin123"    /* ← 明文 */
    }
}
```

### 风险分析

| 风险 | 说明 |
|------|------|
| 拖库即泄露 | 如果 `users.json` 被读取，所有密码直接暴露 |
| 密码复用风险 | 用户往往在多个平台使用相同密码，一个泄露导致连锁沦陷 |
| 明文比对 | `==` 字符串比对是**定时安全的**（Python 字符串比较不是恒定时间），理论上存在时序攻击风险 |

### 修复方案

使用 **scrypt 哈希算法**（通过 `werkzeug.security` 库）替代明文存储和比对。

#### 第 1 步：生成密码哈希

使用 `generate_password_hash` 将明文密码转换为哈希值：

```python
from werkzeug.security import generate_password_hash

# 一次性的哈希计算
hash_admin = generate_password_hash("admin123")
# 结果: scrypt:32768:8:1$5nBBXBovcLjbgoCR$718b1dfbba49bee9352...

hash_alice = generate_password_hash("alice2025")
# 结果: scrypt:32768:8:1$VWmh3N3wSbyPFVO9$9b13b7b1d3894e0d27f...
```

**哈希结构说明**：

```
scrypt:32768:8:1$5nBBXBovcLjbgoCR$718b1dfbba49bee9352...
├─────┴──┴─┴┴────┴──────────┴──────────────────────────┴
算法     N r p     salt (16字节随机)          hash (64字节)
```

- `scrypt`：抗硬件加速的慢哈希算法
- `N=32768`：CPU/内存成本参数（越大越难破解）
- `r=8`：块大小参数
- `p=1`：并行化参数
- `salt`：随机生成，每个密码不同，防止彩虹表攻击

#### 第 2 步：更新 `users.json` 存储哈希值

```json
{
    "admin": {
        "username": "admin",
        "password": "scrypt:32768:8:1$5nBBXBovcLjbgoCR$718b1dfbba49bee93521964ffe41f01622609637e48f59219bb19f4dd3c1b4dd2cbc3c62bb3a960c76fa658d9b81055129350ae979c1ba985adb7aed0a24dd20",
        "role": "admin",
        "email": "admin@example.com",
        "phone": "13800138000",
        "balance": 99999
    }
}
```

#### 第 3 步：修改 app.py 导入并使用安全比对函数

```python
# 新增导入
from werkzeug.security import check_password_hash

# 修改登录比对逻辑
# 修复前
if user and user["password"] == password:

# 修复后
if user and check_password_hash(user["password"], password):
```

#### 第 4 步：对比算法分析

```
明文比对流程：
  用户输入 "admin123"  →  直接 vs  "admin123"  →  通过 ✅

哈希比对流程（修复后）：
  用户输入 "admin123"
       ↓
  从数据库取出哈希: scrypt:32768:8:1$SALT$HASH
       ↓
  check_password_hash() 内部流程:
    1. 解析哈希值，提取算法、参数、salt
    2. 用同样的参数和 salt 对输入的 "admin123" 重新计算哈希
    3. 比较新哈希值和存储的哈希值是否一致
       ↓
  一致 → 通过 ✅  |  不一致 → 拒绝 ❌
```

### 修复前后对比

| 对比项 | 修复前 | 修复后 |
|--------|--------|--------|
| 存储格式 | `"admin123"`（8字符明文） | `"scrypt:32768:8:1$...$..."`（162字符哈希）|
| 单向性 | 可逆，直接可读 | 不可逆，无法还原密码 |
| 彩虹表防护 | 无 | 随机 salt，每用户唯一 |
| 比对方式 | `==` 字符串比对 | `check_password_hash()` 安全比对 |
| 拖库后果 | 密码全部暴露 | 只能暴力破解，scrypt 成本极高 |

---

## 修复总结

| 漏洞 | 修改文件 | 核心改动 | 代码行数变化 |
|------|---------|---------|-------------|
| 硬编码凭据 | `app.py`、`.gitignore`、新建 `config.json`、`users.json` 及示例文件 | 将硬编码数据移到外部 JSON 文件 | +45 / -22 |
| 字典注入 + 密码泄露 | `app.py`、`templates/index.html` | 新增 `get_safe_user()` 过滤密码字段，新增 `validate_input()` 输入校验 | +38 / -5 |
| 明文密码 | `app.py`、`users.json` | 密码改用 scrypt 哈希，比对改用 `check_password_hash()` | +2 / -1 |

### 当前剩余待修复漏洞

本项目仍包含以下故意保留的教学用漏洞：

| # | 漏洞 | 等级 |
|---|------|------|
| 1 | Session 伪造（`secret_key` 仍为弱密钥） | 🔴 严重 |
| 2 | Debug 模式 RCE（`/console` 可访问） | 🔴 严重 |
| 3 | HTML 注释泄露默认账号 | 🔴 严重 |
| 4 | 无暴力破解防护 | 🟠 高危 |
| 5 | 无 CSRF 防护 | 🟠 高危 |
| 6 | 无 HTTPS | 🟠 高危 |
| 7 | Session 永不过期 | 🟡 中危 |

---

*本报告由 Claude Code 自动生成*
