import subprocess
import sys
import os

current_dir = os.path.dirname(__file__)

scripts = [
    os.path.join(current_dir, 'AI_jiqizhixin.py'),
    os.path.join(current_dir, 'AI_MITNews.py'),
    os.path.join(current_dir, 'AI_summary.py'),
    os.path.join(current_dir, 'daily_md_generator.py'),
    os.path.join(current_dir, 'auto_push_github.py'),
]

for script in scripts:
    print(f'运行: {script}')
    try:
        result = subprocess.run([sys.executable, script], check=True)
    except subprocess.CalledProcessError as e:
        print(f'执行 {script} 时出错: {e}')
    except Exception as e:
        print(f'未知错误: {e}') 