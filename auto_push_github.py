import os
import subprocess
from datetime import datetime

def git_commit_and_push():
   # 从环境变量读取hugo项目路径，如果未设置，则默认为用户本地的绝对路径
    # 在 GitHub Action 中，你需要设置 HUGO_PROJECT_PATH 这个 secret
    hugo_src = os.getenv('HUGO_PROJECT_PATH', r'C:\Users\kongg\0')
    
    # Hugo 源目录和 public 目录
    public_dir = os.path.join(hugo_src, 'public')

    # 1. 先在 hugo_src 下执行 hugo 命令，生成 public 目录
    os.chdir(hugo_src)
    try:
        # 使用 --quiet 参数减少输出，忽略一些非致命错误
        subprocess.run(['hugo', '--quiet'], check=False)
    except subprocess.CalledProcessError as e:
        print(f"Hugo 构建失败: {e}")
        return

    # 2. 再切换到 public 目录，执行 git 操作
    os.chdir(public_dir)
    if not os.path.exists(os.path.join(public_dir, '.git')):
        print(f"目录 {public_dir} 不是一个git仓库，请先在该目录下初始化或clone你的仓库。")
        return
    subprocess.run(['git', 'pull'], check=True)
    subprocess.run(['git', 'add', '.'], check=True)
    commit_msg = f"每日自动同步: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    try:
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
    except subprocess.CalledProcessError:
        print("无改动，无需提交。")
        return
    subprocess.run(['git', 'push'], check=True)
    print("同步完成！")

if __name__ == '__main__':
    git_commit_and_push() 