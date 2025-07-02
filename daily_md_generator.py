import os
import json
import hashlib
from datetime import datetime, timedelta
import glob
import re

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

# 计算内容的MD5哈希值，用于去重
def get_content_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

# 获取前一天的日期目录
def get_previous_day_folder():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday_safe = yesterday.replace('-', '_')
    return os.path.join(target_root, yesterday_safe)

# 收集前几天生成的所有index.md文件的内容哈希
def collect_existing_content_hashes(days=3):
    content_hash_set = set()
    
    # 遍历最近几天的文件夹
    for day_offset in range(1, days+1):
        day_date = (datetime.now() - timedelta(days=day_offset)).strftime('%Y-%m-%d')
        day_folder = os.path.join(target_root, day_date.replace('-', '_'))
        
        if not os.path.exists(day_folder):
            continue
            
        # 查找所有index.md文件
        for root, dirs, files in os.walk(day_folder):
            for file in files:
                if file.lower() == 'index.md':
                    index_path = os.path.join(root, file)
                    try:
                        with open(index_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 提取正文部分（去除front matter）
                            match = re.search(r'^\+\+\+\n.*?\+\+\+\n(.*)', content, re.DOTALL)
                            if match:
                                content_body = match.group(1)
                                content_hash = get_content_hash(content_body)
                                content_hash_set.add(content_hash)
                    except Exception as e:
                        print(f"读取文件失败 {index_path}: {e}")
    
    print(f"已收集 {len(content_hash_set)} 个现有内容哈希值用于去重")
    return content_hash_set

def generate_daily_news_folders():
    today = datetime.now().strftime('%Y-%m-%d')
    today_safe = today.replace('-', '_')
    today_folder = os.path.join(target_root, today_safe)
    os.makedirs(today_folder, exist_ok=True)

    # 收集已存在的内容哈希值
    existing_content_hashes = collect_existing_content_hashes()

    summary_jsonl = find_latest_summary_jsonl()
    if not summary_jsonl or not os.path.exists(summary_jsonl):
        print('未找到 summarized_articles.jsonl，请先运行 AI_summary.py')
        return
    with open(summary_jsonl, 'r', encoding='utf-8') as f:
        articles = [json.loads(line) for line in f if line.strip()]

    # 记录处理结果
    total_articles = len(articles)
    skipped_articles = 0
    generated_articles = 0

    # 每条新闻一个子文件夹，内有index.md
    for idx, article in enumerate(articles):
        title = article.get('title', f'news_{idx+1}')
        summary = article.get('summary', '')
        url = article.get('url', '')
        original_content = article.get('original_content', '')
        
        # 生成文章内容
        head = [
            "+++\n",
            f"date = '{datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')}'\n",
            "draft = false\n",
            f"title = '{title}'\n",
        ]
        
        # 如果有URL，添加到front matter，但不使用完整URL，只保留相对路径
        if url:
            # 移除协议部分，避免Hugo构建错误
            cleaned_url = url.replace('http://', '').replace('https://', '')
            head.append(f"url = '{cleaned_url}'\n")
            
        head.append("+++\n\n")
        
        # 内容部分：AI摘要作为首页显示内容
        content_body = summary + '\n\n'
        
        # 添加原文链接和原文摘要，但使用纯文本形式而非Markdown链接
        if url:
            content_body += f"## 原文链接\n\n{title}\n{url}\n\n"
        
        if original_content:
            content_body += f"## 原文摘要\n\n{original_content}\n\n"
            
        # 检查内容是否已存在（去重）
        content_hash = get_content_hash(content_body)
        if content_hash in existing_content_hashes:
            print(f"⏭️ 跳过重复内容: {title}")
            skipped_articles += 1
            continue
        
        # 内容不重复，生成文件夹和index.md
        folder_name = f"{idx+1:02d}_{safe_filename(title)}"
        news_folder = os.path.join(today_folder, folder_name)
        os.makedirs(news_folder, exist_ok=True)
        index_md_path = os.path.join(news_folder, 'index.md')
        
        # 合成完整内容
        full_content = ''.join(head) + content_body
        
        # 写入文件
        with open(index_md_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
            
        # 记录已生成
        generated_articles += 1
        existing_content_hashes.add(content_hash)  # 防止当天内重复

    print(f'总计: {total_articles} 篇文章')
    print(f'已生成: {generated_articles} 篇')
    print(f'已跳过: {skipped_articles} 篇(重复内容)')
    print(f'全部归类于: {today_folder}')

if __name__ == '__main__':
    generate_daily_news_folders() 