import os
import subprocess
import sys
from datetime import datetime

def run_command(command, cwd, silent=False):
    """在指定目录下运行命令并处理错误"""
    try:
        if not silent:
            print(f"▶️ 在 {cwd} 中执行: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        if not silent and result.stdout.strip():
            print(f"   输出: {result.stdout.strip()}")
        if not silent and result.stderr.strip():
            print(f"   错误输出: {result.stderr.strip()}")
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {' '.join(e.cmd)}")
        print(f"   返回码: {e.returncode}")
        if e.stdout.strip():
            print(f"   输出:\n{e.stdout.strip()}")
        if e.stderr.strip():
            print(f"   错误输出:\n{e.stderr.strip()}")
        return False, None
    except Exception as e:
        print(f"❌ 发生未知错误: {e}")
        return False, None

def main():
    """
    该脚本首先运行hugo构建站点, 然后在public目录中执行Git操作。
    - 在本地运行时, 它会 commit 但不会 push。
    - 在GitHub Actions中, 它会完成 commit 和 push。
    """
    # --- 智能路径和环境配置 ---
    is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
    hugo_source_path = ''
    
    if is_github_actions:
        hugo_source_path = os.getenv('HUGO_PROJECT_PATH')
        if not hugo_source_path:
            print("❌ 错误: 在GitHub Actions中运行时必须设置HUGO_PROJECT_PATH环境变量")
            sys.exit(1)
        print(f"🤖 在GitHub Actions中运行, Hugo源路径: {hugo_source_path}")
    else:
        hugo_source_path = r'C:\Users\kongg\0'
        print(f"💻 在本地运行, Hugo源路径: {hugo_source_path}")
    
    public_path = os.path.join(hugo_source_path, 'public')
    # --- 配置结束 ---

    # --- 1. 运行Hugo构建 ---
    print("\n--- 步骤1: 构建Hugo站点 ---")
    if not os.path.isdir(hugo_source_path):
        print(f"❌ 错误: Hugo源路径不存在: {hugo_source_path}")
        sys.exit(1)
    
    success, _ = run_command(['hugo'], cwd=hugo_source_path)
    if not success:
        print("❌ Hugo构建失败, 终止操作")
        sys.exit(1)
    print("✅ Hugo站点构建成功")
    
    # --- 2. 在public目录中执行Git操作 ---
    print(f"\n--- 步骤2: 在public目录中执行Git操作 ---")
    if not os.path.isdir(public_path):
        print(f"❌ 错误: public目录不存在: {public_path}")
        sys.exit(1)
    
    # 检查public是否是Git仓库
    if not os.path.isdir(os.path.join(public_path, '.git')):
        print(f"❌ 错误: {public_path} 不是一个Git仓库")
        sys.exit(1)
    
    if is_github_actions:
        commit_email = os.getenv('GIT_COMMIT_EMAIL', 'github-actions[bot]@users.noreply.github.com')
        commit_name = os.getenv('GIT_COMMIT_NAME', 'github-actions[bot]')
        
        # 配置远程URL, 包含认证信息
        repo_url = os.getenv('PAGES_REPO_URL')
        branch = os.getenv('PAGES_BRANCH')
        if not repo_url or not branch:
            print("❌ 错误: Actions环境中缺少PAGES_REPO_URL或PAGES_BRANCH。")
            sys.exit(1)

        if '/' not in repo_url:
            print(f"❌ 错误: PAGES_REPO_URL 格式不正确, 应该是 'owner/repo', 但收到了 '{repo_url}'")
            sys.exit(1)
        
        # --- 使用 GH_PAT 进行认证 ---
        # PAT是属于某个用户的, 所以actor必须是PAT的所有者, 而不是 github-actions[bot]
        # 我们假设PAT的所有者就是目标仓库的所有者
        token = os.getenv('GH_PAT')
        if not token:
            print("❌ 错误: 必须在 Actions Secret 中提供 GH_PAT 用于认证。")
            sys.exit(1)
            
        actor = repo_url.split('/')[0] # 从 "owner/repo" 中提取 "owner"
        
        remote_url = f"https://{actor}:{token}@github.com/{repo_url}.git"
        run_command(['git', 'remote', 'set-url', 'origin', remote_url], cwd=public_path, silent=True)
        
        run_command(['git', 'config', 'user.email', commit_email], cwd=public_path)
        run_command(['git', 'config', 'user.name', commit_name], cwd=public_path)

    # 添加所有更改
    print("添加更改到暂存区...")
    run_command(['git', 'add', '.'], cwd=public_path)
    
    # 检查是否有更改需要提交
    success, status_output = run_command(['git', 'status', '--porcelain'], cwd=public_path, silent=True)
    if not status_output:
        print("✅ 没有检测到更改, 无需提交")
        sys.exit(0)
    
    # 提交更改
    commit_message = f"docs: 发布每日更新 {datetime.now().strftime('%Y-%m-%d')}"
    print(f"提交更改: {commit_message}")
    success, _ = run_command(['git', 'commit', '-m', commit_message], cwd=public_path)
    if not success:
        print("❌ 提交失败")
        sys.exit(1)
    print("✅ 提交成功")
    
    # 仅在GitHub Actions中推送
    if is_github_actions:
        print("🚀 推送到远程仓库...")
        # 直接推送到指定的远端和分支
        success, _ = run_command(['git', 'push', 'origin', f'HEAD:{branch}'], cwd=public_path)
        if success:
            print("🎉 成功推送到远程仓库!")
        else:
            print("❌ 推送失败")
            sys.exit(1)
    else:
        print("ℹ️ 在本地环境中跳过推送, 请手动执行 'git push'")

if __name__ == "__main__":
    main() 