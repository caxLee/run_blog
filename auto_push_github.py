import os
import subprocess
from datetime import datetime

def git_commit_and_push():
    # 步骤 1: 获取 Hugo 项目路径
    hugo_project_path = os.getenv('HUGO_PROJECT_PATH', r'C:\Users\kongg\0')
    print(f"Hugo project path: {hugo_project_path}")

    if not os.path.isdir(hugo_project_path):
        print(f"❌ 错误：找不到指定的 Hugo 项目路径: {hugo_project_path}")
        return

    # 步骤 2: 构建 Hugo 站点
    print("🚀 正在构建 Hugo 站点...")
    try:
        # 使用 cwd 参数明确指定工作目录，而不是依赖 os.chdir
        hugo_process = subprocess.run(
            ['hugo'], 
            cwd=hugo_project_path,  # <-- 核心改动
            check=True, 
            capture_output=True, 
            text=True
        )
        print("✅ Hugo 站点构建成功。")
        print(hugo_process.stdout)
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
        subprocess.run(['git', 'config', 'user.name', 'github-actions[bot]'], cwd=hugo_project_path, check=True)
        subprocess.run(['git', 'config', 'user.email', 'github-actions[bot]@users.noreply.github.com'], cwd=hugo_project_path, check=True)

        print("➕ 正在将改动添加到 Git...")
        # 明确在hugo项目根目录下执行git add
        subprocess.run(['git', 'add', 'content/', 'public/', 'data/'], cwd=hugo_project_path, check=True) 
        
    else:
        # 在本地环境中，只有 public 目录是 Git 仓库
        public_dir = os.path.join(hugo_project_path, 'public')
        print(f"💻 在本地环境中，切换到 public 目录 ({public_dir}) 进行提交...")
        
        try:
            # 对于本地场景，os.chdir 依旧是简单有效的方式
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
    # 为保证路径正确，提交和推送也在指定目录下执行
    git_dir_to_run = hugo_project_path if is_github_actions else os.path.join(hugo_project_path, 'public')
    
    status_result = subprocess.run(['git', 'status', '--porcelain'], cwd=git_dir_to_run, check=True, capture_output=True, text=True)
    if not status_result.stdout.strip():
        print("ℹ️ 无改动，无需提交。")
        return

    print(f"💬 正在提交改动: '{commit_msg}'")
    try:
        subprocess.run(['git', 'commit', '-m', commit_msg], cwd=git_dir_to_run, check=True)
    except subprocess.CalledProcessError:
        # 在某些情况下，即使有暂存文件，也可能没有有效提交（例如只有空目录更改）
        print("ℹ️ 无可提交的改动。")
        return

    # 步骤 5: 推送到远程仓库
    print("⏫ 正在推送到远程仓库...")
    subprocess.run(['git', 'push'], cwd=git_dir_to_run, check=True)

    print("🎉 同步完成！所有任务已成功执行！")

if __name__ == '__main__':
    git_commit_and_push() 