import os
import json
from datetime import datetime
import glob

# 自动定位 summarized_articles.jsonl 的最新文件
# 优先查找 AI_summary.py 生成的路径
# 兼容多平台

def find_latest_summary_jsonl():
    # 1. 先查找 AI_summary.py 里的 base_dir 路径
    candidate = os.path.join(r'C:\Users\kongg\0\spiders\ai_news', 'summarized_articles.jsonl')
    if os.path.exists(candidate):
        return candidate
    # 2. 其次查找当前目录及子目录下所有同名文件，取最新
    files = glob.glob('**/summarized_articles.jsonl', recursive=True)
    if files:
        files = sorted(files, key=lambda x: os.path.getmtime(x), reverse=True)
        return files[0]
    return None

# 目标根目录
# 例如：C:\Users\kongg\0\content\post
# 可根据实际情况调整
# 这里假设与原逻辑一致
# 你可以根据实际Hugo路径修改 target_root
#
target_root = r'C:\Users\kongg\0\content\post'

def safe_filename(name):
    # 生成安全的文件夹名
    return ''.join(c if c.isalnum() or c in '-_.' else '_' for c in name)[:40]

def generate_daily_news_folders():
    today = datetime.now().strftime('%Y-%m-%d')
    today_safe = today.replace('-', '_')
    today_folder = os.path.join(target_root, today_safe)
    os.makedirs(today_folder, exist_ok=True)

    summary_jsonl = find_latest_summary_jsonl()
    if not summary_jsonl or not os.path.exists(summary_jsonl):
        print('未找到 summarized_articles.jsonl，请先运行 AI_summary.py')
        return
    with open(summary_jsonl, 'r', encoding='utf-8') as f:
        articles = [json.loads(line) for line in f if line.strip()]

    # 每条新闻一个子文件夹，内有index.md
    for idx, article in enumerate(articles):
        title = article.get('title', f'news_{idx+1}')
        summary = article.get('summary', '')
        # 生成安全的文件夹名
        folder_name = f"{idx+1:02d}_{safe_filename(title)}"
        news_folder = os.path.join(today_folder, folder_name)
        os.makedirs(news_folder, exist_ok=True)
        index_md_path = os.path.join(news_folder, 'index.md')
        # 头部元信息
        head = [
            "+++\n",
            f"date = '{datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')}'\n",
            "draft = true\n",
            f"title = '{title}'\n",
            "+++\n\n"
        ]
        # 内容
        content = ''.join(head) + summary + '\n'
        with open(index_md_path, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f'已为{len(articles)}条新闻生成独立文件夹和index.md')
    print(f'全部归类于: {today_folder}')

if __name__ == '__main__':
    generate_daily_news_folders() 