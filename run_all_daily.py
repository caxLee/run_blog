import subprocess
import sys
import os
import platform

current_dir = os.path.dirname(__file__)

scripts = [
    os.path.join(current_dir, 'AI_jiqizhixin.py'),
    os.path.join(current_dir, 'AI_MITNews.py'),
    os.path.join(current_dir, 'AI_summary.py'),
    os.path.join(current_dir, 'daily_md_generator.py'),
    os.path.join(current_dir, 'auto_push_github.py'),
]

# 检测是否在GitHub Actions环境中运行
is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'

# 设置环境变量
if is_github_actions:
    # 在GitHub Actions中，设置工作目录为当前目录
    os.environ['HUGO_PROJECT_PATH'] = os.getcwd()
    print(f"在GitHub Actions中运行，HUGO_PROJECT_PATH设为: {os.getcwd()}")

# 确保所有必要的目录都存在
def ensure_directories():
    """确保所有必要的目录结构都存在"""
    base_dir = os.getcwd() if is_github_actions else r'C:\Users\kongg\0'
    
    # 创建爬虫数据目录
    spider_dir = os.path.join(base_dir, 'spiders', 'ai_news')
    os.makedirs(spider_dir, exist_ok=True)
    print(f"确保目录存在: {spider_dir}")
    
    # 创建内容目录
    content_dir = os.path.join(base_dir, 'content', 'post')
    os.makedirs(content_dir, exist_ok=True)
    print(f"确保目录存在: {content_dir}")

    # 创建public目录（可选）
    public_dir = os.path.join(base_dir, 'public')
    os.makedirs(public_dir, exist_ok=True)
    print(f"确保目录存在: {public_dir}")

# 确保所有必要的目录都存在
ensure_directories()

# 运行脚本
for script in scripts:
    print(f'运行: {script}')
    try:
        # 在GitHub Actions中，添加环境变量
        env = os.environ.copy()
        if is_github_actions:
            env['PYTHONIOENCODING'] = 'utf-8'
            
        result = subprocess.run([sys.executable, script], check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f'执行 {script} 时出错: {e}')
    except Exception as e:
        print(f'未知错误: {e}') 