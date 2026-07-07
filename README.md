# Flask 用户信息管理平台

一个简易的用户信息管理平台，基于 Python Flask 构建，**专门用于 Web 安全漏洞教学与练习**。

> ⚠️ **免责声明**：本项目包含大量故意引入的安全漏洞，仅用于安全学习、CTF 训练和渗透测试教学。**请勿部署到生产环境。**

---

## 功能

- 用户登录 / 登出
- 用户信息展示（用户名、邮箱、手机、角色、余额）
- 基于 session 的登录状态管理

## 内置账号

| 用户名 | 密码 | 角色 | 余额 |
|--------|------|------|------|
| `admin` | `admin123` | admin | 99999 |
| `alice` | `alice2025` | user | 100 |

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
python app.py

# 3. 访问
http://localhost:5000
```

## 项目结构

```
flask-user-manager/
├── app.py                 # 主应用
├── config.json            # 配置文件（密钥、端口等）[已 gitignore]
├── config.example.json    # 配置示例
├── users.json             # 用户数据 [已 gitignore]
├── users.example.json     # 用户数据示例
├── requirements.txt       # Python 依赖清单
├── LICENSE                # MIT 开源许可证
├── .gitignore
├── .github/workflows/
│   └── python-test.yml    # CI 自动测试
├── static/
│   └── css/
│       └── style.css      # 样式文件
└── templates/
    ├── base.html           # 基础模板（导航栏）
    ├── index.html          # 首页
    └── login.html          # 登录页
```

## 安全漏洞清单

本项目用于演示以下 Web 安全漏洞：

| # | 漏洞 | 严重程度 |
|---|------|----------|
| 1 | Session 伪造（弱密钥） | 🔴 严重 |
| 2 | Debug 模式远程代码执行 | 🔴 严重 |
| 3 | HTML 注释泄露默认账号 | 🔴 严重 |
| 4 | 无暴力破解防护 | 🟠 高危 |
| 5 | 无 CSRF 防护 | 🟠 高危 |
| 6 | 无 HTTPS 明文传输 | 🟠 高危 |
| 7 | Session 永不过期 | 🟡 中危 |
| 8 | 监听 0.0.0.0 暴露内网 | 🟡 中危 |

## 学习目标

- 理解 Session 伪造原理与 Flask 签名机制
- 掌握密码哈希存储的必要性
- 学习输入校验与数据过滤
- 理解 CSRF、暴力破解等常见攻击方式
