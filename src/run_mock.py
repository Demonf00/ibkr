import os
import sys

# 强制设置环境变量，确保走 Mock 模式和 paper 配置
os.environ["BROKER_MODE"] = "mock"
os.environ["APP_ENV"] = "paper"

# 引入你的主程序
from main import main

if __name__ == "__main__":
    print("=== 启动 Mock 沙盒交易测试 ===")
    print("目标: 验证 V-AR 与 Quality Trend 策略的信号对抗与风控逻辑\n")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n=== 测试结束 ===")
        sys.exit(0)