import os
import json
import hashlib
import shutil
from datetime import datetime, timedelta
import glob
import re
import sys

# --- 智能路径配置 ---
is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
hugo_project_path = ''

if is_github_actions:
    # 在 GitHub Actions 中, HUGO_PROJECT_PATH 必须由 workflow 提供
    hugo_project_path = os.getenv('HUGO_PROJECT_PATH')
    if not hugo_project_path:
        print("❌ 错误: 在 GitHub Actions 环境中, 环境变量 HUGO_PROJECT_PATH 未设置。")
        sys.exit(1)
    print(f"🤖 在 GitHub Actions 中运行, Hugo 项目路径: {hugo_project_path}")
else:
    # 在本地运行时, 使用固定的绝对路径
    hugo_project_path = r'C:\Users\kongg\0'
    print(f"💻 在本地运行, Hugo 项目路径: {hugo_project_path}")
    # 检查本地路径是否存在
    if not os.path.isdir(hugo_project_path):
        print(f"⚠️ 警告: 本地 Hugo 路径不存在, 请检查路径是否正确: {hugo_project_path}")
        # 脚本将继续运行, 但依赖此路径的操作可能会失败
# --- 路径配置结束 ---

# 自动定位 summarized_articles.jsonl 的最新文件
# 优先查找 AI_summary.py 生成的路径
# 兼容多平台

def find_latest_summary_jsonl():
    # 1. 先查找 AI_summary.py 里的 base_dir 路径
    # 使用在上面配置好的全局变量 hugo_project_path
    candidate = os.path.join(hugo_project_path, 'spiders', 'ai_news', 'summarized_articles.jsonl')
    if os.path.exists(candidate):
        return candidate
    # 2. 其次查找当前目录及子目录下所有同名文件，取最新
    files = glob.glob('**/summarized_articles.jsonl', recursive=True)
    if files:
        files = sorted(files, key=lambda x: os.path.getmtime(x), reverse=True)
        return files[0]
    return None

# 从环境变量读取hugo项目路径，如果未设置，则脚本会提前退出
# hugo_project_path = os.getenv('HUGO_PROJECT_PATH') # 已在顶部定义和检查

# 目标根目录
# 例如：C:\Users\kongg\0\content\post
# 可根据实际情况调整
# 这里假设与原逻辑一致
# 你可以根据实际Hugo路径修改 target_root
#
target_root = os.path.join(hugo_project_path, 'content', 'post')

def safe_filename(name):
    # 生成安全的文件夹名
    return ''.join(c if c.isalnum() or c in '-_.' else '_' for c in name)[:40]

# 计算内容的MD5哈希值，用于去重
def get_content_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

# 计算标题的哈希值，用于检测相同标题的文章
def get_title_hash(title):
    # 移除所有空格和标点符号，转为小写后计算哈希值
    normalized_title = ''.join(c.lower() for c in title if c.isalnum())
    return hashlib.md5(normalized_title.encode('utf-8')).hexdigest()

# 获取前一天的日期目录
def get_previous_day_folder():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday_safe = yesterday.replace('-', '_')
    return os.path.join(target_root, yesterday_safe)

# 收集已存在的文章信息，包括内容哈希和标题哈希
def collect_existing_articles_info(days=7):
    content_hash_set = set()  # 内容哈希集合
    title_hash_map = {}       # 标题哈希 -> 文件夹路径的映射
    
    # 遍历最近几天的文件夹
    for day_offset in range(0, days+1):  # 包括今天(0)
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
                            
                            # 提取标题
                            title_match = re.search(r"title\s*=\s*'([^']*)'", content)
                            if title_match:
                                title = title_match.group(1)
                                title_hash = get_title_hash(title)
                                # 保存标题哈希和对应的文件夹路径
                                title_hash_map[title_hash] = os.path.dirname(index_path)
                            
                            # 提取正文部分（去除front matter）
                            content_match = re.search(r'^\+\+\+\n.*?\+\+\+\n(.*)', content, re.DOTALL)
                            if content_match:
                                content_body = content_match.group(1)
                                content_hash = get_content_hash(content_body)
                                content_hash_set.add(content_hash)
                    except Exception as e:
                        print(f"读取文件失败 {index_path}: {e}")
    
    print(f"已收集 {len(content_hash_set)} 个现有内容哈希值和 {len(title_hash_map)} 个标题哈希值用于去重")
    return content_hash_set, title_hash_map

# 检查当天文件夹中是否存在重复文章，如果有则删除
def remove_duplicates_in_today_folder(today_folder):
    if not os.path.exists(today_folder):
        return 0
        
    content_hashes = {}  # 内容哈希 -> 文件夹路径
    title_hashes = {}    # 标题哈希 -> 文件夹路径
    duplicates = []      # 要删除的重复文件夹
    
    # 第一遍：收集所有文章的哈希值
    for item in os.listdir(today_folder):
        item_path = os.path.join(today_folder, item)
        if os.path.isdir(item_path):
            index_path = os.path.join(item_path, 'index.md')
            if os.path.exists(index_path):
                try:
                    with open(index_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # 提取标题
                        title_match = re.search(r"title\s*=\s*'([^']*)'", content)
                        if title_match:
                            title = title_match.group(1)
                            title_hash = get_title_hash(title)
                            
                            # 检查标题是否重复
                            if title_hash in title_hashes:
                                duplicates.append(item_path)
                                print(f"⚠️ 发现重复标题: {title}")
                                continue
                            title_hashes[title_hash] = item_path
                        
                        # 提取正文部分
                        content_match = re.search(r'^\+\+\+\n.*?\+\+\+\n(.*)', content, re.DOTALL)
                        if content_match:
                            content_body = content_match.group(1)
                            content_hash = get_content_hash(content_body)
                            
                            # 检查内容是否重复
                            if content_hash in content_hashes:
                                duplicates.append(item_path)
                                print(f"⚠️ 发现重复内容: {title}")
                                continue
                            content_hashes[content_hash] = item_path
                except Exception as e:
                    print(f"读取文件失败 {index_path}: {e}")
    
    # 第二遍：删除重复的文件夹
    for dup_path in duplicates:
        try:
            shutil.rmtree(dup_path)
            print(f"🗑️ 删除重复文件夹: {os.path.basename(dup_path)}")
        except Exception as e:
            print(f"删除文件夹失败 {dup_path}: {e}")
    
    return len(duplicates)

def generate_daily_news_folders():
    today = datetime.now().strftime('%Y-%m-%d')
    today_safe = today.replace('-', '_')
    today_folder = os.path.join(target_root, today_safe)
    
    # 确保目录存在
    os.makedirs(today_folder, exist_ok=True)
    print(f"创建文章目录: {today_folder}")
    
    # 先清理当天文件夹中的重复文章
    removed_count = remove_duplicates_in_today_folder(today_folder)
    if removed_count > 0:
        print(f"已删除当天文件夹中的 {removed_count} 个重复文章")

    # 收集已存在的文章信息
    existing_content_hashes, existing_title_hash_map = collect_existing_articles_info()

    summary_jsonl = find_latest_summary_jsonl()
    if not summary_jsonl or not os.path.exists(summary_jsonl):
        print('未找到 summarized_articles.jsonl，请先运行 AI_summary.py')
        return
    print(f"使用摘要文件: {summary_jsonl}")
    with open(summary_jsonl, 'r', encoding='utf-8') as f:
        articles = [json.loads(line) for line in f if line.strip()]

    # 记录处理结果
    total_articles = len(articles)
    skipped_articles = 0
    generated_articles = 0
    duplicate_title_count = 0

    # 当前处理的文章内容哈希集合，用于防止当天内重复
    today_content_hashes = set()
    today_title_hashes = set()

    # 每条新闻一个子文件夹，内有index.md
    for idx, article in enumerate(articles):
        title = article.get('title', f'news_{idx+1}')
        summary = article.get('summary', '')
        url = article.get('url', '')
        original_content = article.get('original_content', '')
        
        # --- 诊断日志: 开始 ---
        print(f"\n--- 正在检查文章: \"{title}\"")
        # --- 诊断日志: 结束 ---

        # 检查标题是否重复
        title_hash = get_title_hash(title)
        # --- 诊断日志: 开始 ---
        print(f"    - 标题哈希: {title_hash}")
        # --- 诊断日志: 结束 ---
        if title_hash in existing_title_hash_map:
            duplicate_folder = existing_title_hash_map[title_hash]
            print(f"⏭️ 跳过重复标题: {title}")
            print(f"   已存在于: {duplicate_folder}")
            skipped_articles += 1
            continue
        
        if title_hash in today_title_hashes:
            print(f"⏭️ 跳过当天重复标题: {title}")
            skipped_articles += 1
            continue

        # --- 新代码: 解析标签并清理摘要 ---
        summary_raw = article.get('summary', '')
        summary = summary_raw
        tags = []
        # 正则表达式查找 "标签：[...]" 或 "标签:[...]"
        tags_match = re.search(r'标签：\s*\[(.*?)\]', summary_raw, re.DOTALL)
        if tags_match:
            # 提取中括号内的内容
            tags_str = tags_match.group(1)
            # 按逗号分割，并清理每个标签的空格和引号
            tags = [tag.strip().strip('"').strip("'") for tag in tags_str.split(',') if tag.strip()]
            
            # 从摘要中移除标签部分
            summary = re.sub(r'标签：\s*\[.*?\]', '', summary_raw).strip()
            # 移除可能存在的 "摘要：" 前缀
            summary = re.sub(r'^摘要：\s*', '', summary).strip()
        # --- 代码结束 ---
        
        # 生成文章内容
        head = [
            "+++\n",
            f"date = '{datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')}'\n",
            "draft = false\n",
            f"title = '{title}'\n",
        ]
        
        # 如果解析出了标签，则添加到 front matter
        if tags:
            tags_formatted = ", ".join([f'"{tag}"' for tag in tags])
            head.append(f"tags = [{tags_formatted}]\n")

        # 如果有URL，添加到front matter，但不使用完整URL，只保留相对路径
        if url:
            # 移除协议部分，避免Hugo构建错误
            cleaned_url = url.replace('http://', '').replace('https://', '')
            head.append(f"url = '{cleaned_url}'\n")
            
        head.append("+++\n\n")
        
        # 内容部分：使用清理后的AI摘要, 并添加'more'分隔符，供Hugo主题使用
        content_body = summary + '\n\n<!--more-->\n\n'
        
        # 添加原文链接
        if url:
            content_body += f"## 原文链接\n\n{url}\n\n"
            
        # 检查内容是否已存在（去重）
        content_hash = get_content_hash(content_body)
        # --- 诊断日志: 开始 ---
        print(f"    - 内容哈希: {content_hash}")
        # --- 诊断日志: 结束 ---
        if content_hash in existing_content_hashes:
            print(f"⏭️ 跳过重复内容: {title}")
            print(f"    - 原因: 内容哈希值与一篇旧文章匹配。")
            skipped_articles += 1
            continue
        
        if content_hash in today_content_hashes:
            print(f"⏭️ 跳过当天重复内容: {title}")
            print(f"    - 原因: 内容哈希值与当天已处理的文章匹配。")
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
        today_content_hashes.add(content_hash)  # 防止当天内重复
        today_title_hashes.add(title_hash)      # 防止当天内重复标题

    print(f'总计: {total_articles} 篇文章')
    print(f'已生成: {generated_articles} 篇')
    print(f'已跳过: {skipped_articles} 篇(重复内容或标题)')
    print(f'全部归类于: {today_folder}')

if __name__ == '__main__':
    generate_daily_news_folders() 