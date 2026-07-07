import json
import os
from flask import Flask, render_template, request, redirect, session

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


@app.route("/")
def index():
    username = session.get("username")
    user = USERS.get(username) if username else None
    return render_template("index.html", user=user)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = USERS.get(username)
        if user and user["password"] == password:
            session["username"] = username
            return render_template("index.html", user=user)
        else:
            return render_template("login.html", error="用户名或密码错误")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=debug, host="0.0.0.0", port=port)
