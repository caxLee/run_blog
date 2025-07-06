import os
import subprocess
from datetime import datetime

def git_commit_and_push():
    # 步骤 1: 获取 Hugo 项目路径并切换目录
    # 增加了默认值 r'C:\Users\kongg\0' 以便在本地独立运行时也能找到路径
    hugo_project_path = os.getenv('HUGO_PROJECT_PATH', r'C:\Users\kongg\0')
    
    print(f"Hugo project path: {hugo_project_path}")
    
    # 切换到 Hugo 项目的根目录，这是运行 hugo 命令所必需的
    try:
        os.chdir(hugo_project_path)
    except FileNotFoundError:
        print(f"❌ 错误：找不到指定的 Hugo 项目路径: {hugo_project_path}")
        return

    # 步骤 2: 构建 Hugo 站点
    print("🚀 正在构建 Hugo 站点...")
    try:
        subprocess.run(['hugo'], check=True, capture_output=True, text=True)
        print("✅ Hugo 站点构建成功。")
    except FileNotFoundError:
        print("❌ 错误：找不到 'hugo' 命令。请确保 Hugo 已安装并在系统的 PATH 中。")
        return
    except subprocess.CalledProcessError as e:
        print(f"❌ Hugo 构建失败: {e}")
        print(f"Hugo stderr: {e.stderr}")
        print(f"Hugo stdout: {e.stdout}")
        return

    # 步骤 3: 根据环境执行不同的 Git 操作
    is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
    commit_msg = f"每日自动同步: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    if is_github_actions:
        # 在 GitHub Actions 中，整个项目是一个 Git 仓库
        print("🤖 在 GitHub Actions 环境中，提交源码和构建结果...")
        
        print("👤 正在配置 Git 用户...")
        subprocess.run(['git', 'config', 'user.name', 'github-actions[bot]'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'github-actions[bot]@users.noreply.github.com'], check=True)

        print("➕ 正在将改动添加到 Git...")
        subprocess.run(['git', 'add', 'content/', 'public/'], check=True)
        
    else:
        # 在本地环境中，只有 public 目录是 Git 仓库
        public_dir = os.path.join(hugo_project_path, 'public')
        print(f"💻 在本地环境中，切换到 public 目录 ({public_dir}) 进行提交...")
        
        try:
            os.chdir(public_dir)
        except FileNotFoundError:
            print(f"❌ 错误：找不到 public 目录: {public_dir}")
            return
        
        if not os.path.isdir('.git'):
             print(f"❌ 错误：public 目录 ({public_dir}) 不是一个 Git 仓库。")
             return

        print("➕ 正在将改动添加到 Git...")
        subprocess.run(['git', 'add', '.'], check=True)

    # 步骤 4: 检查状态并提交
    # 这一步对于本地和云端是通用的
    status_result = subprocess.run(['git', 'status', '--porcelain'], check=True, capture_output=True, text=True)
    if not status_result.stdout.strip():
        print("ℹ️ 无改动，无需提交。")
        return

    print(f"💬 正在提交改动: '{commit_msg}'")
    try:
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
    except subprocess.CalledProcessError:
        print("ℹ️ 无改动，无需提交。")
        return

    # 步骤 5: 推送到远程仓库
    print("⏫ 正在推送到远程仓库...")
    subprocess.run(['git', 'push'], check=True)

    print("🎉 同步完成！所有任务已成功执行！")

if __name__ == '__main__':
    git_commit_and_push() 