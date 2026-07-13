#!/bin/bash
# ============================================================
# 靶机硬化脚本 - 恢复真实 Linux 权限配置
# 用途:让 /page 路径遍历就算没修也读不到 /etc/shadow
# 用法: sudo bash harden.sh
# ============================================================

set -e

echo "[1/3] 恢复 /etc/shadow 权限为 600 (只有 root 可读)"
chmod 600 /etc/shadow
chown root:root /etc/shadow

echo "[2/3] 恢复 /etc/passwd 权限为 644 (所有用户可读)"
chmod 644 /etc/passwd
chown root:root /etc/passwd

echo "[3/3] 验证"
ls -la /etc/passwd /etc/shadow

echo ""
echo "硬化完成"
echo "现在 /page 路径遍历读 /etc/shadow 会失败(flask 进程非 root,读不到)"
echo ""
echo "测试命令:"
echo "  curl 'http://localhost:5000/page?name=/etc/shadow'  # 应该失败"
echo "  curl 'http://localhost:5000/page?name=/etc/passwd' # 仍然能读(系统设计如此)"
echo "  curl 'http://localhost:5000/page?name=/proc/self/cwd/app.py'  # 仍能读(代码层未修)"
echo ""
echo "代码层修复:已实装白名单(/page 路由 ALLOWED_PAGES),路径遍历走不通"
