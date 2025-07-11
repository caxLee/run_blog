import subprocess
import sys
import os

# 获取脚本所在的当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 定义要按顺序运行的脚本列表
scripts_to_run = [
    'AI_jiqizhixin.py',
    'AI_MITNews.py',
    'AI_summary.py',
    'daily_md_generator.py',
    'auto_push_github.py',
]

print("🚀 开始执行每日构建流程...")

# 依次执行定义好的脚本
for script_name in scripts_to_run:
    script_path = os.path.join(current_dir, script_name)
    print(f"\n▶️ 正在运行: {script_name}")
    try:
        # 使用 subprocess.run 来执行脚本
        # check=True 会在脚本返回非零退出码时抛出异常
        result = subprocess.run(
            [sys.executable, script_path], 
            check=True, 
            capture_output=True, # 捕获输出
            text=True # 以文本形式解码输出
        )
        print(f"✅ {script_name} 执行成功。")
        if result.stdout:
            print("   --- 输出 ---")
            print(result.stdout)
            print("   --- 输出结束 ---")

    except subprocess.CalledProcessError as e:
        print(f"❌ 执行 {script_name} 时出错！")
        print(f"   - 返回码: {e.returncode}")
        if e.stdout:
            print("   --- 标准输出 ---")
            print(e.stdout)
        if e.stderr:
            print("   --- 错误输出 ---")
            print(e.stderr)
        # 脚本执行失败，中止整个流程
        sys.exit(1) 
    except FileNotFoundError:
        print(f"❌ 错误：脚本文件未找到: {script_path}")
        sys.exit(1)

print("\n🎉 所有脚本执行完毕。") 