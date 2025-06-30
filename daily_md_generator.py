import os
from datetime import datetime

# 源摘要md文件
current_dir = os.path.dirname(__file__)
summary_md = os.path.join(current_dir, 'summarized_articles.md')

# 目标根目录
target_root = r'C:\Users\kongg\0\content\post'

def generate_daily_folder_and_md():
    today = datetime.now().strftime('%Y-%m-%d')
    today_safe = today.replace('-', '_')  # 用下划线代替横杠
    today_folder = os.path.join(target_root, today_safe)
    os.makedirs(today_folder, exist_ok=True)

    # 生成index.md路径
    index_md_path = os.path.join(today_folder, 'index.md')

    # 生成title
    title = f"{today_safe}要闻"

    # 生成头部元信息
    head = [
        "+++\n",
        f"date = '{datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')}'\n",
        "draft = true\n",
        f"title = '{title}'\n",
        "+++\n\n"
    ]

    # 读取当天摘要内容
    if not os.path.exists(summary_md):
        print('summarized_articles.md 不存在')
        return
    with open(summary_md, 'r', encoding='utf-8') as f:
        summary_content = f.read()

    # 合成新md内容
    new_md_content = ''.join(head) + summary_content

    # 写入index.md
    with open(index_md_path, 'w', encoding='utf-8') as f:
        f.write(new_md_content)

    print(f'已生成: {index_md_path}')

if __name__ == '__main__':
    generate_daily_folder_and_md() 