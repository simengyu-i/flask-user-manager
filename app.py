import json
import os
import sqlite3
import magic
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)

# 从配置文件加载
config_path = os.path.join(os.path.dirname(__file__), "config.json")
users_path = os.path.join(os.path.dirname(__file__), "users.json")

with open(config_path, encoding="utf-8") as f:
    config = json.load(f)

with open(users_path, encoding="utf-8") as f:
    USERS = json.load(f)

app.secret_key = config.get("secret_key", "dev-key-2025")
port = config.get("port", 5000)
debug = config.get("debug", True)

# ── 上传配置 ──
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── 数据库初始化 ──
def init_db():
    db_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "users.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            balance REAL DEFAULT 100
        )
    """)
    # 兼容旧表：添加 balance 列（若不存在则静默忽略）
    try:
        c.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 100")
    except sqlite3.OperationalError:
        pass

    # 插入默认用户（明文密码 + 余额）
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone, balance) VALUES ('admin', 'admin123', 'admin@example.com', '13800138000', 99999)")
    c.execute("INSERT OR IGNORE INTO users (username, password, email, phone, balance) VALUES ('alice', 'alice2025', 'alice@example.com', '13900139001', 100)")
    conn.commit()
    conn.close()


init_db()


def get_safe_user(username):
    """返回不包含密码的用户信息"""
    user = USERS.get(username)
    if user:
        return {k: v for k, v in user.items() if k != "password"}
    return None


def validate_input(value):
    """基础输入校验：只允许字母、数字、中文、@、.、-、_"""
    import re
    if not value or not isinstance(value, str):
        return False
    return bool(re.match(r'^[a-zA-Z0-9一-鿿@.\-_]+$', value))


@app.route("/")
def index():
    username = session.get("username")
    user = get_safe_user(username) if username else None
    return render_template("index.html", user=user)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # 输入校验
        if not validate_input(username) or not validate_input(password):
            return render_template("login.html", error="输入包含非法字符")

        user = USERS.get(username)
        if user and check_password_hash(user["password"], password):
            session["username"] = username
            safe_user = get_safe_user(username)
            return render_template("index.html", user=safe_user)
        else:
            return render_template("login.html", error="用户名或密码错误")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ── 注册 ──
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")

        db_path = os.path.join(os.path.dirname(__file__), "data", "users.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # 使用参数化查询修复 SQL 注入
        sql = "INSERT INTO users (username, password, email, phone, balance) VALUES (?, ?, ?, ?, 0)"
        print(f"[SQL] {sql}")

        try:
            c.execute(sql, (username, password, email, phone))
            conn.commit()
            return render_template("login.html", error="注册成功，请登录")
        except Exception as e:
            return render_template("register.html", error=f"注册失败：{e}")
        finally:
            conn.close()

    return render_template("register.html")


# ── 搜索 ──
@app.route("/search")
def search():
    keyword = request.args.get("keyword", "")
    results = []
    sql = ""

    if keyword:
        db_path = os.path.join(os.path.dirname(__file__), "data", "users.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # 使用参数化查询修复 SQL 注入
        sql = "SELECT id, username, email, phone FROM users WHERE username LIKE ? OR email LIKE ?"
        print(f"[SQL] {sql}")

        try:
            c.execute(sql, (f"%{keyword}%", f"%{keyword}%"))
            results = c.fetchall()
        except Exception as e:
            print(f"[SQL ERROR] {e}")
            results = []
        finally:
            conn.close()

    username = session.get("username")
    user = get_safe_user(username) if username else None
    return render_template("index.html", user=user, results=results, keyword=keyword)


# ── 头像上传 ──
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "username" not in session:
        return redirect("/login")

    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename:
            # 修复 1：secure_filename 防止路径遍历
            filename = secure_filename(file.filename)

            # 修复 2：白名单扩展名
            if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS:
                return render_template("upload.html", error="不支持的文件类型，仅允许 jpg、jpeg、png、gif")

            # 修复 3：MIME 校验
            mime = magic.from_buffer(file.read(1024), mime=True)
            file.seek(0)
            if mime not in ['image/jpeg', 'image/png', 'image/gif']:
                return render_template("upload.html", error="文件 MIME 类型不匹配")

            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)

            # 修复 4：内容二次渲染
            try:
                im = Image.open(save_path)
                im.save(save_path)
            except Exception:
                os.remove(save_path)
                return render_template("upload.html", error="文件内容不是有效图片")

            file_url = url_for("static", filename=f"uploads/{filename}")
            return render_template("upload.html", filename=filename, file_url=file_url)
        else:
            return render_template("upload.html", error="请选择一个文件")

    return render_template("upload.html")


# ── 个人中心 ──
@app.route("/profile")
def profile():
    if "username" not in session:
        return redirect("/login")

    # 获取当前登录用户自己的 id
    db_path = os.path.join(os.path.dirname(__file__), "data", "users.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (session["username"],))
    login_row = c.fetchone()
    if not login_row:
        conn.close()
        return redirect("/login")
    login_user_id = login_row[0]

    user_id = request.args.get("user_id")
    if not user_id:
        user_id = str(login_user_id)

    # 水平越权修复：只能查看自己的资料
    if int(user_id) != login_user_id:
        conn.close()
        return "无权查看其他用户的资料"

    sql = "SELECT id, username, email, phone, balance FROM users WHERE id = ?"
    c.execute(sql, (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return "用户不存在"
    user_info = {
        "id": row[0], "username": row[1],
        "email": row[2], "phone": row[3],
        "balance": row[4]
    }
    return render_template("profile.html", user=user_info)


# ── 充值 ──
@app.route("/recharge", methods=["POST"])
def recharge():
    if "username" not in session:
        return redirect("/login")

    # 获取当前登录用户自己的 id
    db_path = os.path.join(os.path.dirname(__file__), "data", "users.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (session["username"],))
    login_row = c.fetchone()
    if not login_row:
        conn.close()
        return redirect("/login")
    login_user_id = login_row[0]

    user_id = request.form.get("user_id")
    amount_str = request.form.get("amount", "0")

    # 垂直越权修复：只能给自己的账号充值
    if int(user_id) != login_user_id:
        conn.close()
        return "无权为其他用户充值"

    # 业务逻辑修复：金额必须大于 0
    try:
        amount = float(amount_str)
    except ValueError:
        conn.close()
        return "金额格式无效"
    if amount <= 0:
        conn.close()
        return "充值金额必须大于 0"

    sql = "UPDATE users SET balance = balance + ? WHERE id = ?"
    print(f"[SQL] {sql}")
    c.execute(sql, (amount, user_id))
    conn.commit()
    conn.close()
    return redirect(f"/profile?user_id={user_id}")


# ── 动态页面加载(Path Traversal 修复)──
# 修复方式:白名单 —— 只允许加载预定义页面,任何不在白名单的 name 全部拒绝
ALLOWED_PAGES = {"help", "about", "contact", "faq"}


@app.route("/page")
def page():
    name = request.args.get("name", "")

    # 修复 1:白名单校验 —— 任何不在白名单的 name 直接拒绝,杜绝路径遍历
    if name not in ALLOWED_PAGES:
        username = session.get("username")
        user = get_safe_user(username) if username else None
        return render_template("index.html", user=user,
                                page_content="页面不存在", page_not_found=True)

    # 修复 2:路径拼接现在安全(name 来自白名单,只能是合法标识符)
    base_dir = os.path.join(os.path.dirname(__file__), "pages")
    file_path = os.path.join(base_dir, name + ".html")

    if os.path.exists(file_path) and os.path.isfile(file_path):
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    else:
        content = None

    username = session.get("username")
    user = get_safe_user(username) if username else None

    if content is None:
        return render_template("index.html", user=user,
                                page_content="页面不存在", page_not_found=True)
    return render_template("index.html", user=user,
                            page_content=content, page_not_found=False)


if __name__ == "__main__":
    app.run(debug=debug, host="0.0.0.0", port=port)
