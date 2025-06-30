import os
import json
import asyncio
import time
from dotenv import load_dotenv
from openai import OpenAI
from seatable_api import Base
from playwright.async_api import async_playwright
from requests.exceptions import ReadTimeout
from bs4 import BeautifulSoup

# ========== 环境加载 ==========
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")
SEATABLE_API_TOKEN = os.getenv("SEATABLE_API_TOKEN")
SEATABLE_SERVER_URL = os.getenv("SEATABLE_SERVER_URL")

# ========== 初始化 ==========
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)
base = Base(SEATABLE_API_TOKEN, SEATABLE_SERVER_URL)
base.auth()
table_name = "AI摘要"

# ========== 去重用 ==========
base_dir = r'C:\Users\kongg\0\spiders\ai_news'
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
async def generate_summaries(title, content):
    try:
        print(f"✏️ 正在生成摘要: {title}")

        # 中文摘要
        res_zh = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一位资深科技编辑，擅长提炼复杂文章的核心内容。请用简洁、专业、准确的语言，生成一段不超过150字的中文摘要，概括文章的主要观点、关键数据与结论，避免主观评价，保持新闻报道风格。"},
                {"role": "user", "content": f"以下是文章正文，请为其撰写专业摘要：\n\n{content}"},
            ],
            temperature=0.5,
        )
        summary_zh = res_zh.choices[0].message.content.strip()

        # 英文摘要
        res_en = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional tech journalist with expertise in summarizing complex articles. Please generate a concise and informative summary (no more than 100 words) that captures the article's key points, findings, and implications. Avoid subjective opinions and use a neutral, journalistic tone."},
                {"role": "user", "content": f"Here is the article content. Please write a high-quality English summary:\n\n{content}"},
            ],
            temperature=0.5,
        )
        summary_en = res_en.choices[0].message.content.strip()

        return summary_zh, summary_en

    except Exception as e:
        print(f"\n❌ 摘要生成失败: {title}\n原因: {e}")
        return None, None


# ========== 增加超时重试的函数 ==========
def safe_append_row_with_retry(base, table_name, row, retries=3, delay=5):
    for attempt in range(retries):
        try:
            insert_result = base.append_row(table_name, row)
            return insert_result
        except ReadTimeout as e:
            print(f"⚠️ 尝试 {attempt + 1} 失败，超时错误: {e}")
            if attempt < retries - 1:
                print(f"⏳ 等待 {delay} 秒后重试...")
                time.sleep(delay)
            else:
                print("❌ 重试次数已耗尽，跳过插入。")
                return None
        except Exception as e:
            print(f"⚠️ 出现其他错误: {e}")
            return None

# ========== 主爬虫逻辑 ==========
async def main():
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    os.makedirs(os.path.dirname(markdown_file), exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
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

                # 插入 SeaTable，增加超时重试
                insert_result = safe_append_row_with_retry(base, table_name, row)
                if insert_result:
                    print(f"✅ 已插入 SeaTable: {title}")

                # 等待一段时间再处理下一篇
                await page.wait_for_timeout(1000)

        await browser.close()

# 运行爬虫
asyncio.run(main())
