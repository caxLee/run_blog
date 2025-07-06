import os
import subprocess
from datetime import datetime

def git_commit_and_push():
    # Hugo 项目的根目录就是当前工作目录
    hugo_src = os.getcwd()
    print(f"Hugo project path: {hugo_src}")
            
    # 步骤 1: 构建 Hugo 站点
    # 移除 --quiet 以便在 Actions 日志中看到完整的 Hugo 输出
    print("🚀 正在构建 Hugo 站点...")
    try:
        subprocess.run(['hugo'], check=True, capture_output=True, text=True)
        print("✅ Hugo 站点构建成功。")
    except subprocess.CalledProcessError as e:
        print(f"❌ Hugo 构建失败: {e}")
        print(f"Hugo stderr: {e.stderr}")
        print(f"Hugo stdout: {e.stdout}")
        return

    # 步骤 2: 配置 Git 用户
    print("👤 正在配置 Git 用户...")
    subprocess.run(['git', 'config', 'user.name', 'github-actions[bot]'], check=True)
    subprocess.run(['git', 'config', 'user.email', 'github-actions[bot]@users.noreply.github.com'], check=True)

    # 步骤 3: 添加变动文件并提交
    print("➕ 正在将改动添加到 Git...")
    # 同时添加新生成的 markdown 源文件和 public 目录下的构建结果
    subprocess.run(['git', 'add', 'content/', 'public/'], check=True)
    
    # 检查是否有文件被暂存
    status_result = subprocess.run(['git', 'status', '--porcelain'], check=True, capture_output=True, text=True)
    if not status_result.stdout.strip():
        print("ℹ️ 无改动，无需提交。")
        return

    commit_msg = f"每日自动同步: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    print(f"💬 正在提交改动: '{commit_msg}'")
    subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
    # 步骤 4: 推送到远程仓库
    print("⏫ 正在推送到远程仓库...")
    subprocess.run(['git', 'push'], check=True)
    print("🎉 同步完成！所有任务已成功执行！")

if __name__ == '__main__':
    git_commit_and_push() 