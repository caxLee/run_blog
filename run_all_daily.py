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

# 在GitHub Actions中，创建必要的目录结构
if is_github_actions:
    spiders_dir = os.path.join(os.getcwd(), 'spiders', 'ai_news')
    os.makedirs(spiders_dir, exist_ok=True)
    print(f"创建目录: {spiders_dir}")

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