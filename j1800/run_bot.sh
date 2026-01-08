#!/bin/bash

# 这是一个守护脚本，用于在 J1800 上持续运行 car_bot.py
# 如果脚本崩溃，它会自动重启。

# 请确保路径正确，建议放在 /home/ubuntu/LaoJia-main/ 下
cd "$(dirname "$0")"

echo "🚀 Starting LaoJia J1800 Bot..."

# 尝试自动激活虚拟环境 (支持 venv 或 .venv)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Activated virtual environment: venv"
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Activated virtual environment: .venv"
else
    echo "ℹ️ No virtual environment found, using system Python"
fi

while true; do
    echo "----------------------------------------"
    echo "⏰ $(date): Starting python script..."
    
    # 运行 Python 脚本 (使用当前环境的 python)
    python car_bot.py
    
    # 如果脚本退出（崩溃），等待 10 秒后重启
    echo "⚠️ Script exited. Restarting in 10 seconds..."
    sleep 10
done
