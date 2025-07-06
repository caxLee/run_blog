import os
import subprocess
from datetime import datetime
import shutil

def git_commit_and_push():
    # 从环境变量读取hugo项目路径
    hugo_src = os.getenv('HUGO_PROJECT_PATH')
    if not hugo_src:
        # 在 GitHub Actions 中，如果未设置，则默认为当前工作目录
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            hugo_src = os.getcwd()
            print(f"HUGO_PROJECT_PATH 未设置，在 Actions 中默认为: {hugo_src}")
        else:
            print("⚠️ 未找到 HUGO_PROJECT_PATH 环境变量，跳过 git 同步。")
            return

    public_dir = os.path.join(hugo_src, 'public')

    # 步骤 1: 确保 public 目录是一个 Git 仓库
    is_git_repo = os.path.isdir(os.path.join(public_dir, '.git'))

    if not is_git_repo:
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            print(f"🏃 在 GitHub Actions 中，目录 '{public_dir}' 不是 Git 仓库，尝试自动克隆...")
            repo_url = os.environ.get('PAGES_REPO_URL')
            branch = os.environ.get('PAGES_BRANCH')

            if not repo_url or not branch:
                print("❌ 自动克隆失败：请在 GitHub Secrets 中设置 PAGES_REPO_URL 和 PAGES_BRANCH。")
                return

            if os.path.isdir(public_dir):
                shutil.rmtree(public_dir)

            try:
                print(f"🔄 正在从 {repo_url} 克隆分支 {branch} 到 {public_dir}...")
                subprocess.run(
                    ['git', 'clone', '--branch', branch, '--single-branch', '--depth', '1', repo_url, public_dir],
                    check=True
                )
                print("✅ 成功克隆发布仓库。")
            except subprocess.CalledProcessError as e:
                print(f"❌ 克隆发布仓库失败: {e}")
                return
        else:
            print(f"⚠️ 目录 {public_dir} 不是一个 Git 仓库。请在本地手动设置。")
            return
            
    # 步骤 2: 构建 Hugo 站点
    os.chdir(hugo_src)
    if shutil.which('hugo') is None:
        print("⚠️ 未检测到 Hugo 可执行文件，跳过站点构建步骤。")
    else:
        try:
            print("🚀 正在构建 Hugo 站点...")
            # Hugo 会保留 .git 目录，但会清理其他文件
            subprocess.run(['hugo', '--quiet'], check=False)
        except subprocess.CalledProcessError as e:
            print(f"Hugo 构建失败: {e}")
            return

    # 步骤 3: 切换到 public 目录，执行 git 操作
    os.chdir(public_dir)
    
    # 检查 Git 状态，避免无意义的提交
    status_result = subprocess.run(['git', 'status', '--porcelain'], check=True, capture_output=True, text=True)
    if not status_result.stdout.strip():
        print("ℹ️ 无改动，无需提交。")
        return

    print("➕ 正在将改动添加到 Git...")
    subprocess.run(['git', 'add', '.'], check=True)
    
    commit_msg = f"每日自动同步: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    print(f"💬 正在提交改动: '{commit_msg}'")
    try:
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
    except subprocess.CalledProcessError:
        # 理论上，前面的状态检查已经处理了这种情况，但作为保险
        print("ℹ️ 无改动，无需提交。")
        return
        
    print("⏫ 正在推送到远程仓库...")
    subprocess.run(['git', 'push'], check=True)
    print("✅ 同步完成！")

if __name__ == '__main__':
    git_commit_and_push() 