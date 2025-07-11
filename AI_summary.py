import os
import json
import hashlib
from openai import OpenAI
from tqdm import tqdm
from dotenv import load_dotenv
import sys

# 检查是否在GitHub Actions环境中运行
is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'


load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")

# ========== 初始化 ==========
# 使用 OpenAI v1.x+ 内置的重试机制
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
    timeout=60.0,  # 设置较长的超时时间
    max_retries=5, # 内置的重试次数
)


base = None  # SeaTable disabled
table_name = 'AI摘要'  # preserved as placeholder, not used

# --- 环境自适应的智能路径配置 ---
hugo_project_path = ''
# 首先检查是否在 GitHub Actions 环境中
if os.environ.get('GITHUB_ACTIONS') == 'true':
    print("🤖 [AI_summary.py] 在 GitHub Actions 中运行, 将使用环境变量。")
    hugo_project_path = os.getenv('HUGO_PROJECT_PATH')
    if not hugo_project_path:
        print("❌ 错误: 在 GitHub Actions 环境中, 环境变量 HUGO_PROJECT_PATH 未设置。")
        sys.exit(1)
else:
    # 如果不在云端，则假定为本地环境，自动计算路径
    print("💻 [AI_summary.py] 在本地运行, 将自动检测项目路径。")
    hugo_project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print(f"✅ [AI_summary.py] 使用 Hugo 项目路径: {hugo_project_path}")
# --- 路径配置结束 ---

# 文件路径现在完全基于 hugo_project_path
base_dir = os.path.join(hugo_project_path, 'spiders', 'ai_news')
input_files = [
    os.path.join(base_dir, "mit_news_articles.jsonl"),
    os.path.join(base_dir, "jiqizhixin_articles_summarized.jsonl")
]
output_file = os.path.join(base_dir, "summarized_articles.jsonl")
markdown_file = os.path.join(base_dir, "summarized_articles.md")  # 新增Markdown文件名

# 用于去重的内容哈希集合
content_hash_set = set()

# 用于计算内容哈希值
def get_content_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

# 加载已总结的标题集合和内容哈希集合
summarized_titles = set()
if os.path.exists(output_file):
    with open(output_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                summarized_titles.add(data["title"])
                # 同时记录内容哈希值，用于去重
                if "original_content" in data:
                    content_hash = get_content_hash(data["original_content"])
                    content_hash_set.add(content_hash)
            except:
                continue

# 添加重试逻辑
def call_openai_with_retry(model, messages, temperature=0.7, response_format=None):
    """使用内置重试调用OpenAI API"""
    params = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        params["response_format"] = response_format
    return client.chat.completions.create(**params)

# 处理所有输入文件
articles = []
for input_file in input_files:
    if not os.path.exists(input_file):
        print(f"⚠️ 输入文件不存在: {input_file}")
        continue
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get("title") and data.get("content"):
                    # 检查内容是否重复
                    content_hash = get_content_hash(data["content"])
                    if content_hash in content_hash_set:
                        print(f"⏭️ 跳过重复内容: {data['title']}")
                        continue
                    
                    # 如果是新内容，则添加到处理队列，同时记录哈希值
                    articles.append(data)
                    content_hash_set.add(content_hash)
            except Exception as e:
                print(f"⚠️ 解析JSON失败: {e}")

# 生成摘要
print(f"开始生成摘要，共 {len(articles)} 篇，已有摘要 {len(summarized_titles)} 篇")

# 确保输出目录存在
os.makedirs(os.path.dirname(output_file), exist_ok=True)
os.makedirs(os.path.dirname(markdown_file), exist_ok=True)

# 插入数据并写入 jsonl
with open(output_file, 'a', encoding='utf-8') as out_f, \
     open(markdown_file, 'a', encoding='utf-8') as md_f:  # 同时打开Markdown文件
    for article in tqdm(articles, desc="🌐 正在生成摘要"):
        title = article["title"]
        content = article["content"]
        url = article.get("url", "") # 获取URL
        
        # 如果标题已存在，跳过
        if title in summarized_titles:
            print(f"⏭️ 跳过已处理的标题: {title}")
            continue

        try:
            # 增加更多调试信息
            print(f"正在为文章 '{title}' 调用OpenAI API生成摘要...")
            # 调用 GPT-3.5 生成摘要（带重试）
            keywords = ["基模", "多模态", "Infra", "AI4S", "具身智能", "垂直大模型", "Agent", "能效优化"]
            keywords_str = ", ".join(f'"{k}"' for k in keywords)
            messages = [
                {"role": "system", "content": f"你是一名专业的新闻编辑。请根据以下新闻原文，完成两项任务：\n1. **生成摘要**: 撰写一段3-5句话的中文摘要，客观、准确地概括文章的核心内容。\n2. **提取关键词**: 从以下列表中精确选择1-3个最相关的关键词：[{keywords_str}]。\n\n你的输出必须是严格的JSON格式，包含两个键：'summary'（其值为摘要字符串）和'tags'（其值为关键词字符串数组）。"},
                {"role": "user", "content": f"新闻原文：\n{content}"}
            ]
            response = call_openai_with_retry(
                "gpt-3.5-turbo", 
                messages, 
                temperature=0.5,
                response_format={"type": "json_object"}
            )

            response_data = json.loads(response.choices[0].message.content.strip())
            summary = response_data.get("summary", "")
            tags = response_data.get("tags", [])


            # 保存摘要到 jsonl 文件
            # 保存原文链接和内容
            article_data = {
                "title": title, 
                "summary": summary,
                "tags": tags,
                "url": url,  # 保存原文链接
                "original_content": ""  # 不再保存原文内容
            }
            out_f.write(json.dumps(article_data, ensure_ascii=False) + "\n")
            out_f.flush()
            summarized_titles.add(title)
            # 写入Markdown
            md_f.write(f"## {title}\n\n")
            if url:
                md_f.write(f"**原文链接：** [{url}]({url})\n\n")
            if tags:
                md_f.write(f"**标签：** {', '.join(tags)}\n\n")
            md_f.write(f"**摘要：**\n\n{summary}\n\n")
            md_f.write("---\n\n")
            md_f.flush()

            print(f"✅ 成功生成并保存摘要: {title}")

        except Exception as e:
            print(f"\n❌ 摘要生成失败: {title}\n原因: {e}")