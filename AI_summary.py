import os
import json
import hashlib
from openai import OpenAI
from tqdm import tqdm
from dotenv import load_dotenv

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

# 从环境变量读取hugo项目路径，如果未设置，则默认为用户本地的绝对路径
# 在 GitHub Action 中，你需要设置 HUGO_PROJECT_PATH 这个 secret
hugo_project_path = os.getenv('HUGO_PROJECT_PATH', r'C:\Users\kongg\0')

# 文件路径
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
def call_openai_with_retry(model, messages, temperature=0.7):
    """使用内置重试调用OpenAI API"""
    return client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )

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
            messages = [
                {"role": "system", "content": "你将获得一篇新闻原文，请完成以下任务：\n1. 简洁摘要：用简洁、准确的中文对该新闻进行总结，要求3-5句话，涵盖文章的核心观点、关键信息和主要结论，避免主观评价，保持新闻报道风格。\n2. 主题标签：请为该新闻从给定的关键词列表中选择1到3个最相关的主题标签。每个标签应能高度概括新闻的主要内容或领域。\n输入格式：- 新闻原文- 关键词列表\n输出格式：- 摘要（3-5句话）- 标签：[标签1, ...]\n示例输出：\n摘要：……\n标签：[基模, 多模态]"},
                {"role": "user", "content": f"新闻原文：\n{content}\n\n关键词列表：{keywords}"}
            ]
            response = call_openai_with_retry("gpt-3.5-turbo", messages, temperature=0.7)

            summary = response.choices[0].message.content.strip()

            # 保存摘要到 jsonl 文件
            # 保存原文链接和内容
            article_data = {
                "title": title, 
                "summary": summary,
                "url": url,  # 保存原文链接
                "original_content": content[:500] + ("..." if len(content) > 500 else "")  # 保存部分原文内容作为原文摘要
            }
            out_f.write(json.dumps(article_data, ensure_ascii=False) + "\n")
            out_f.flush()
            summarized_titles.add(title)
            # 写入Markdown
            md_f.write(f"## {title}\n")
            if url:
                md_f.write(f"**原文链接：** [{url}]({url})\n\n")
            md_f.write(f"**摘要：**\n\n{summary}\n\n")
            md_f.write("---\n\n")
            md_f.flush()

            print(f"✅ 成功生成并保存摘要: {title}")

        except Exception as e:
            print(f"\n❌ 摘要生成失败: {title}\n原因: {e}")