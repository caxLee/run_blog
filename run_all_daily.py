import subprocess
import sys
import os
import platform

# ==============================================================================
# 远程 Hugo 仓库配置 (仅在 GitHub Actions 中使用)
# ==============================================================================
# 请确保已在 GitHub Secrets 中设置 HUGO_REPO_URL
# 它指向包含您 Hugo 网站源码（hugo.toml, content, themes 等）的仓库
HUGO_PROJECT_DIR_NAME = "hugo_project" # 将 Hugo 项目克隆到这个子目录中
# ==============================================================================

current_dir = os.path.dirname(os.path.abspath(__file__))
is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'

def setup_hugo_project_path():
    """根据环境准备Hugo项目并设置环境变量"""
    if is_github_actions:
        hugo_repo_url = os.getenv('HUGO_REPO_URL')
        if not hugo_repo_url:
            print("❌ 错误：在 GitHub Actions 中运行，但未设置 HUGO_REPO_URL secret。")
            sys.exit(1)
        
        hugo_project_path = os.path.join(current_dir, HUGO_PROJECT_DIR_NAME)
        print(f"🤖 在 GitHub Actions 中，正在克隆 Hugo 项目到: {hugo_project_path}")
        
        try:
            subprocess.run(
                ['git', 'clone', '--depth', '1', hugo_repo_url, hugo_project_path],
                check=True
            )
            print("✅ 成功克隆 Hugo 项目。")
        except subprocess.CalledProcessError as e:
            print(f"❌ 克隆 Hugo 项目失败: {e}")
            sys.exit(1)
            
        os.environ['HUGO_PROJECT_PATH'] = hugo_project_path
        print(f"HUGO_PROJECT_PATH 已设为: {hugo_project_path}")

    else:
        # 在本地运行时，使用固定的本地路径
        local_hugo_path = r'C:\Users\kongg\0'
        os.environ['HUGO_PROJECT_PATH'] = local_hugo_path
        print(f"💻 在本地运行, HUGO_PROJECT_PATH 设为: {local_hugo_path}")

# --- 主程序开始 ---
# 1. 设置环境
setup_hugo_project_path()

# 2. 确保目录存在 (现在它会在正确的 Hugo 项目中创建目录)
hugo_project_path = os.environ['HUGO_PROJECT_PATH']
spider_dir = os.path.join(hugo_project_path, 'spiders', 'ai_news')
os.makedirs(spider_dir, exist_ok=True)
print(f"确保目录存在: {spider_dir}")

# 3. 定义要运行的脚本
scripts = [
    os.path.join(current_dir, 'AI_jiqizhixin.py'),
    os.path.join(current_dir, 'AI_MITNews.py'),
    os.path.join(current_dir, 'AI_summary.py'),
    os.path.join(current_dir, 'daily_md_generator.py'),
    os.path.join(current_dir, 'auto_push_github.py'),
]

# 4. 运行脚本
for script in scripts:
    print(f"运行: {script}")
    try:
        # 确保所有子进程都能继承到正确的环境变量
        env = os.environ.copy()
        result = subprocess.run([sys.executable, script], check=True, env=env, cwd=current_dir)
    except subprocess.CalledProcessError as e:
        print(f'执行 {script} 时出错: {e}')
    except Exception as e:
        print(f'未知错误: {e}') 