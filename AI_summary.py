import os
import json
from openai import OpenAI
from tqdm import tqdm
from dotenv import load_dotenv
from seatable_api import Base, context


load_dotenv()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
)


SEATABLE_API_TOKEN = os.getenv("SEATABLE_API_TOKEN")
SEATABLE_SERVER_URL = os.getenv("SEATABLE_SERVER_URL")

# 初始化 SeaTable
base = Base(SEATABLE_API_TOKEN, SEATABLE_SERVER_URL)
base.auth()


table_name = 'AI摘要'

# 文件路径，全部修正为C:\Users\kongg\0\spiders\ai_news下
base_dir = r'C:\Users\kongg\0\spiders\ai_news'
input_files = [
    os.path.join(base_dir, "mit_news_articles.jsonl"),
    os.path.join(base_dir, "jiqizhixin_articles_summarized.jsonl")
]
output_file = os.path.join(base_dir, "summarized_articles.jsonl")
markdown_file = os.path.join(base_dir, "summarized_articles.md")  # 新增Markdown文件名

# 加载已总结的标题集合
summarized_titles = set()
if os.path.exists(output_file):
    with open(output_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                summarized_titles.add(data["title"])
            except:
                continue

# 处理所有输入文件
articles = []
for input_file in input_files:
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            if data.get("title") and data.get("content"):
                articles.append(data)

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

        try:
            # 调用 GPT-3.5 生成摘要
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个擅长内容总结的助手，请将用户提供的文章内容生成简洁摘要。"},
                    {"role": "user", "content": f"请总结以下文章内容：\n\n{content}"}],
                temperature=0.7,
            )

            summary = response.choices[0].message.content.strip()

            # 保存摘要到 jsonl 文件
            if title not in summarized_titles:
                out_f.write(json.dumps({"title": title, "summary": summary}, ensure_ascii=False) + "\n")
                out_f.flush()
                summarized_titles.add(title)
                # 写入Markdown
                md_f.write(f"## {title}\n")
                md_f.write(f"**摘要：**\n\n{summary}\n\n")
                md_f.write("---\n\n")
                md_f.flush()

            # 同时将数据插入 SeaTable（不管是否已存在）
            row = {"title": title, "summary": summary}

            # 调试输出，确认数据行
            print(f"正在插入数据到 SeaTable: {row}")

            # 尝试插入到 SeaTable
            insert_result = base.append_row(table_name, row)

            # 调试输出，确认是否插入成功
            print(f"插入结果: {insert_result}")

            print(f"✅ 成功生成并保存摘要: {title}")

        except Exception as e:
            print(f"\n❌ 摘要生成失败: {title}\n原因: {e}")