#!/usr/bin/env bash
# 初始化 project-a 业务仓与 OpenHands（与 config/projects/project-a.yaml repos 相对路径一致）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DESKTOP="$(cd "$ROOT/.." && pwd)"
WEB="$DESKTOP/acme-web"
API="$DESKTOP/acme-api"

export PATH="${HOME}/.local/bin:${PATH:-}"

echo "==> 检查业务仓"
for dir in "$WEB" "$API"; do
  if [[ ! -d "$dir" ]]; then
    echo "缺少目录: $dir（请先创建样板仓）" >&2
    exit 1
  fi
done

if [[ ! -d "$WEB/node_modules" ]]; then
  echo "==> acme-web: npm install"
  (cd "$WEB" && npm install)
else
  echo "==> acme-web: node_modules 已存在，跳过 npm install"
fi

if command -v openhands >/dev/null 2>&1; then
  echo "==> OpenHands: $(openhands --version 2>/dev/null | head -1 || echo ok)"
else
  echo "==> 安装 OpenHands CLI"
  uv tool install openhands --python 3.12
fi

echo ""
echo "完成。可启动："
echo "  cd $API && go run ./cmd/server"
echo "  cd $WEB && npm run dev"
echo "  cd $ROOT && python3 run.py dev --project project-a --prd prds/project-a/PROJ-001_login.md --layer frontend"
