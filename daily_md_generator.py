import os
import json
import hashlib
import shutil
from datetime import datetime, timedelta
import glob
import re
import sys
import pytz

# --- 智能路径配置 ---
# 通过脚本自身位置动态计算项目根目录，不再依赖环境变量
# __file__ 是脚本自身的绝对路径
# os.path.dirname(__file__) 是脚本所在的目录 (e.g., /path/to/project/blogdata)
# os.path.dirname(...) 再一次，就是项目的根目录 (e.g., /path/to/project)
hugo_project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"✅ [daily_md_generator.py] 动态识别 Hugo 项目根目录: {hugo_project_path}")

TARGET_TIMEZONE = pytz.timezone("Asia/Shanghai")
print(f"🕒 使用目标时区: {TARGET_TIMEZONE}")
# --- 路径配置结束 ---

# 自动定位 summarized_articles.jsonl 的最新文件
# 优先查找 AI_summary.py 生成的路径
# 兼容多平台

def find_latest_summary_jsonl():
    # 在多仓库检出的 Actions 环境中, 路径必须是确定的
    # 假设 'scraper_tool' 和 'hugo_source' 在同一个工作区根目录下
    # 并且 AI_summary.py 已经将文件生成到了正确的位置
    # 这个位置应该是由 HUGO_PROJECT_PATH 推断出来的
    summary_path = os.path.join(hugo_project_path, 'spiders', 'ai_news', 'summarized_articles.jsonl')
    
    if os.path.exists(summary_path):
        return summary_path
    
    # 作为备选，在当前工具目录里找
    if os.path.exists('summarized_articles.jsonl'):
        return 'summarized_articles.jsonl'
        
    print(f"⚠️ 警告: 在预设路径 {summary_path} 中未找到摘要文件。")
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

# 确保目标目录存在
os.makedirs(target_root, exist_ok=True)
print(f"确保目标目录存在: {target_root}")

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
    yesterday = (datetime.now(TARGET_TIMEZONE) - timedelta(days=1)).strftime('%Y-%m-%d')
    yesterday_safe = yesterday.replace('-', '_')
    return os.path.join(target_root, yesterday_safe)

# 收集已存在的文章信息，包括内容哈希和标题哈希
def collect_existing_articles_info(days=7):
    content_hash_set = set()  # 内容哈希集合
    title_hash_map = {}       # 标题哈希 -> 文件夹路径的映射
    
    # 遍历最近几天的文件夹
    for day_offset in range(0, days+1):  # 包括今天(0)
        day_date = (datetime.now(TARGET_TIMEZONE) - timedelta(days=day_offset)).strftime('%Y-%m-%d')
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

def get_next_article_index(folder_path):
    if not os.path.exists(folder_path):
        return 1
    
    max_index = 0
    items = os.listdir(folder_path)
    for item in items:
        if os.path.isdir(os.path.join(folder_path, item)):
            match = re.match(r'^(\d+)_', item)
            if match:
                current_index = int(match.group(1))
                if current_index > max_index:
                    max_index = current_index
    return max_index + 1

def generate_daily_news_folders():
    today = datetime.now(TARGET_TIMEZONE).strftime('%Y-%m-%d')
    today_safe = today.replace('-', '_')
    today_folder = os.path.join(target_root, today_safe)
    
    # 确保目录存在
    os.makedirs(today_folder, exist_ok=True)
    print(f"创建文章目录: {today_folder}")

    # 获取当天文章的起始序号
    next_article_index = get_next_article_index(today_folder)
    print(f"今天的文章将从序号 {next_article_index:02d} 开始。")
    
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
        tags = article.get('tags', []) # 直接从JSON获取tags

        # --- 诊断日志: 开始 ---
        print(f"\n--- 正在处理文章: \"{title}\"")
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

        # 内容去重
        content_to_hash = summary + original_content
        content_hash = get_content_hash(content_to_hash)
        # --- 诊断日志: 开始 ---
        print(f"    - 内容哈希: {content_hash}")
        # --- 诊断日志: 结束 ---
        if content_hash in existing_content_hashes:
            print(f"⏭️ 跳过重复内容: {title}")
            skipped_articles += 1
            continue

        if content_hash in today_content_hashes:
            print(f"⏭️ 跳过当天重复内容: {title}")
            skipped_articles += 1
            continue

        # 生成更健壮的文章URL slug
        # 1. 转为小写
        s = title.lower()
        # 2. 移除非法字符 (保留字母、数字、- 和空格)
        s = re.sub(r'[^\w\s-]', '', s)
        # 3. 多个空格或-替换为单个-
        s = re.sub(r'[\s-]+', '-', s).strip('-')
        # 4. 截断
        post_slug = s[:65] # 缩短以容纳前缀


        # 添加数字前缀
        post_slug_with_prefix = f"{next_article_index:02d}_{post_slug}"

        post_folder = os.path.join(today_folder, post_slug_with_prefix)
        os.makedirs(post_folder, exist_ok=True)
        
        # 将当前文章的哈希值加入集合
        today_content_hashes.add(content_hash)
        today_title_hashes.add(title_hash)
        
        # 在子文件夹内创建 index.md
        index_path = os.path.join(post_folder, 'index.md')
        
        # 准备Front Matter
        # 使用 TOML 格式
        # 将tags列表转换为TOML格式的字符串数组
        tags_toml = json.dumps(tags)
        
        # 移除 "摘要：" 和 "标签："
        summary_cleaned = summary.replace("摘要：", "").strip()
        
        front_matter = f"""+++
title = '{title.replace("'", "''")}'
date = "{datetime.now(TARGET_TIMEZONE).isoformat()}"
draft = false
tags = {tags_toml}
summary = "{summary_cleaned.replace('"', '""')[:150]}"
slug = "{post_slug}"
link = "{url}"
+++

{summary_cleaned}

<!--more-->
"""
        
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(front_matter)
            
        print(f"✅ 成功生成文章: {post_slug_with_prefix}")
        generated_articles += 1
        next_article_index += 1 # 为下一篇文章增加序号

    print("\n--- 生成完毕 ---")
    print(f"总共处理文章: {total_articles}")
    print(f"成功生成: {generated_articles}")
    print(f"因重复跳过: {skipped_articles}")
    print("--- --- ---")

if __name__ == '__main__':
    generate_daily_news_folders() 