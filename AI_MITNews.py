import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
import os

BASE_URL = "https://news.mit.edu"
# 使用 HUGO_PROJECT_PATH 以便在 GitHub Action 中也能运行
hugo_project_path = os.getenv('HUGO_PROJECT_PATH', r'C:\Users\kongg\0')
base_dir = os.path.join(hugo_project_path, 'spiders', 'ai_news')
SAVE_PATH = os.path.join(base_dir, "mit_news_articles.jsonl")
MARKDOWN_PATH = os.path.join(base_dir, "mit_news_articles.md")
HEADLESS = True


def load_existing_urls(path):
    if not Path(path).exists():
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return {json.loads(line)["url"] for line in f if line.strip()}


async def scrape_mit_news_articles(save_path):
    # 确保输出目录存在
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    os.makedirs(os.path.dirname(MARKDOWN_PATH), exist_ok=True)
    existing_urls = load_existing_urls(save_path)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context()

        # 加快加载速度：拦截图片、字体等非必要资源
        await context.route("**/*", lambda route: route.abort()
                            if route.request.resource_type in ["image", "font", "media"]
                            else route.continue_())

        page = await context.new_page()
        print("🔗 正在访问 MIT News 首页...")

        # 增加重试逻辑，应对网络波动
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await page.goto(BASE_URL, timeout=60000)
                print("✅ 成功访问 MIT News 首页。")
                break  # 成功，则跳出循环
            except Exception as e:
                print(f"🕒 访问超时 (尝试 {attempt + 1}/{max_retries})，正在重试...")
                if attempt == max_retries - 1:
                    print(f"❌ 访问 MIT News 失败，已达最大重试次数: {e}")
                    await browser.close()
                    return  # 退出函数

        print("🔍 正在提取新闻标题和链接...")
        links = await page.query_selector_all("a.front-page--news-article--teaser--title--link")

        with open(save_path, "a", encoding="utf-8") as f, \
             open(MARKDOWN_PATH, "a", encoding="utf-8") as md_f:
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    title_span = await link.query_selector("span")
                    title = await title_span.inner_text() if title_span else ""

                    if not href or not title.strip():
                        continue  # 跳过无标题的

                    full_url = BASE_URL + href
                    if full_url in existing_urls:
                        print(f"⏭️ 已抓取，跳过：{full_url}")
                        continue

                    print(f"📰 抓取：{title.strip()}")
                    article_page = await context.new_page()
                    await article_page.goto(full_url, timeout=60000)
                    await article_page.wait_for_selector("div.paragraph--type--content-block-text p", timeout=10000)

                    # 获取正文段落
                    paragraphs = await article_page.locator("div.paragraph--type--content-block-text p").all_inner_texts()
                    content = "\n\n".join(paragraphs)

                    data = {
                        "title": title.strip(),
                        "url": full_url,
                        "content": content.strip()
                    }

                    f.write(json.dumps(data, ensure_ascii=False) + "\n")
                    f.flush()

                    # 写入Markdown
                    md_f.write(f"## {title.strip()}\n")
                    md_f.write(f"- 链接: [{full_url}]({full_url})\n\n")
                    md_f.write(f"**正文内容：**\n\n{content.strip()}\n\n")
                    md_f.write("---\n\n")
                    md_f.flush()

                    existing_urls.add(full_url)
                    print(f"✅ 已保存：{title.strip()}")
                    await article_page.close()

                except Exception as e:
                    print(f"❌ 抓取失败: {e}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape_mit_news_articles(SAVE_PATH))
