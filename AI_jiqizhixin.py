import os
import json
import asyncio
import time
import random
from dotenv import load_dotenv
from openai import OpenAI
from playwright.async_api import async_playwright
# SeaTable 相关依赖已移除
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 检查是否在GitHub Actions环境中运行
is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
if is_github_actions:
    print("在GitHub Actions环境中运行")

# ========== 环境加载 ==========
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
SEATABLE_API_TOKEN = os.getenv("SEATABLE_API_TOKEN")
SEATABLE_SERVER_URL = os.getenv("SEATABLE_SERVER_URL")

# ========== 初始化 ==========
# 初始化 OpenAI 客户端，添加更多配置
# 创建具有重试功能的会话
session = requests.Session()
retry_strategy = Retry(
    total=5,  # 最多重试5次
    backoff_factor=1,  # 重试间隔
    status_forcelist=[429, 500, 502, 503, 504],  # 这些HTTP状态码会触发重试
    allowed_methods=["GET", "POST"]  # 允许重试的HTTP方法
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# 使用配置好的会话初始化OpenAI客户端
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE,
    http_client=session,
    timeout=60.0  # 设置较长的超时时间
)
# 已移除 SeaTable 初始化
table_name = "AI摘要"

# ========== 去重用 ==========
# 使用 HUGO_PROJECT_PATH（若未设置则使用当前工作目录）
hugo_project_path = os.getenv('HUGO_PROJECT_PATH', r'C:\Users\kongg\0')
base_dir = os.path.join(hugo_project_path, 'spiders', 'ai_news')
output_file = os.path.join(base_dir, "jiqizhixin_articles_summarized.jsonl")
markdown_file = os.path.join(base_dir, "jiqizhixin_articles_summarized.md")
summarized_titles = set()
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                summarized_titles.add(data["title"])
            except:
                continue

# ========== 摘要生成函数 ==========
# 添加重试逻辑
def call_openai_with_retry(client, model, messages, temperature=0.7, max_retries=5, base_delay=2):
    """使用指数退避重试调用OpenAI API"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                timeout=60.0,  # 明确设置超时时间
                request_timeout=60.0  # 请求超时
            )
            return response
        except Exception as e:
            if attempt == max_retries - 1:  # 最后一次尝试
                raise e
            
            # 指数退避策略
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"API调用失败 (尝试 {attempt+1}/{max_retries})，{delay:.2f}秒后重试: {e}")
            time.sleep(delay)

async def generate_summaries(title, content):
    try:
        print(f"✏️ 正在生成摘要: {title}")

        # 中文摘要（带重试）
        messages_zh = [
            {"role": "system", "content": "你是一位资深科技编辑，擅长提炼复杂文章的核心内容。请用简洁、专业、准确的语言，生成一段不超过150字的中文摘要，概括文章的主要观点、关键数据与结论，避免主观评价，保持新闻报道风格。"},
            {"role": "user", "content": f"以下是文章正文，请为其撰写专业摘要：\n\n{content}"},
        ]
        res_zh = call_openai_with_retry(client, "gpt-3.5-turbo", messages_zh, temperature=0.5)
        summary_zh = res_zh.choices[0].message.content.strip()

        # 英文摘要（带重试）
        messages_en = [
            {"role": "system", "content": "You are a professional tech journalist with expertise in summarizing complex articles. Please generate a concise and informative summary (no more than 100 words) that captures the article's key points, findings, and implications. Avoid subjective opinions and use a neutral, journalistic tone."},
            {"role": "user", "content": f"Here is the article content. Please write a high-quality English summary:\n\n{content}"},
        ]
        res_en = call_openai_with_retry(client, "gpt-3.5-turbo", messages_en, temperature=0.5)
        summary_en = res_en.choices[0].message.content.strip()

        return summary_zh, summary_en

    except Exception as e:
        print(f"\n❌ 摘要生成失败: {title}\n原因: {e}")
        return None, None


# ========== 增加超时重试的函数 ==========
# 已移除 SeaTable 写入函数

# ========== 主爬虫逻辑 ==========
async def main():
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    os.makedirs(os.path.dirname(markdown_file), exist_ok=True)
    async with async_playwright() as p:
        # 在GitHub Actions中使用headless模式，本地开发可视化
        browser = await p.chromium.launch(headless=is_github_actions)
        page = await browser.new_page()
        await page.goto("https://www.jiqizhixin.com/articles", timeout=60000)

        cards = await page.locator("div.article-card").all()

        with open(output_file, "a", encoding="utf-8") as f, \
             open(markdown_file, "a", encoding="utf-8") as md_f:
            for i, card in enumerate(cards):
                time_text = await card.locator("div.article-card__time").inner_text()
                print(f"⏱️ 第 {i + 1} 篇文章时间: {time_text}")

                if "1天前" in time_text:
                    print("🛑 遇到『1天前』，停止抓取。")
                    break

                # 设置监听
                try:
                    async with page.expect_response(
                        lambda res: "/api/v4/articles/" in res.url and res.status == 200,
                        timeout=60000  # 加长等待时间
                    ) as res_info:
                        print("🖱️ 点击文章")
                        await card.click()

                    # 等待页面完全加载
                    await page.wait_for_load_state("load")

                    response = await res_info.value
                    data = await response.json()

                except Exception as e:
                    print(f"⚠️ 页面加载失败，跳过该篇文章: {e}")
                    await page.goto("https://www.jiqizhixin.com/articles", timeout=60000)
                    cards = await page.locator("div.article-card").all()
                    continue

                title = data.get("title")
                published_at = data.get("published_at")
                html_content = data.get("content")

                if not title or not html_content:
                    continue
                if title in summarized_titles:
                    continue

                # 提取纯文本
                soup = BeautifulSoup(html_content, "html.parser")
                content = soup.get_text(separator="\n").strip()

                # 调用 AI 生成摘要
                summary_cn, summary_en = await generate_summaries(title, content)
                if not summary_cn or not summary_en:
                    continue

                row = {
                    "title": title,
                    "published_at": published_at,
                    "content": content,
                    "summary_cn": summary_cn,
                    "summary_en": summary_en,
                }

                # 写入 JSONL
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                summarized_titles.add(title)

                # 写入 Markdown
                md_f.write(f"## {title}\n")
                md_f.write(f"- 发布时间: {published_at}\n\n")
                md_f.write(f"**中文摘要：**\n\n{summary_cn}\n\n")
                md_f.write(f"**English Summary:**\n\n{summary_en}\n\n")
                md_f.write("---\n\n")
                md_f.flush()

                # 已移除写入 SeaTable 的逻辑

                # 等待一段时间再处理下一篇
                await page.wait_for_timeout(1000)

        await browser.close()

# 运行爬虫
asyncio.run(main())
