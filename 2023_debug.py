# -*- coding: utf-8 -*-
import requests
import time
import json
import random
import sys
import re
from collections import defaultdict, Counter
from bs4 import BeautifulSoup
from collections import OrderedDict
from datetime import datetime

PTT_URL = 'https://www.ptt.cc'
BOARD = 'Beauty'
session = requests.Session()
session.cookies.set('over18', '1')

### 1. Crawl
articles = []
popular_articles = []

def is_valid_title(title):
    if not title:
        return False
    title = title.strip()
    if title == "":
        return False
    if '[公告]' in title or 'Fw:[公告]' in title:
        return False
    return True

def parse_index_page(page_url, is_first_page=False, is_last_page=False):
    res = session.get(page_url, timeout=5)
    if res.status_code != 200:
        print(f"無法取得頁面: {page_url}")
        return None
    soup = BeautifulSoup(res.text, 'html.parser')
    entries = soup.select('div.r-ent')

    for entry in entries:
        title_tag = entry.select_one('div.title > a')

        if not title_tag:
            continue
        title = title_tag.text.strip()

        if not is_valid_title(title):
            continue
        url = title_tag['href']
        
        push_tag = entry.select_one('div.nrec').text.strip()
        full_url = PTT_URL + url

        date_tag = entry.select_one('div.date')
        if not date_tag:
            continue

        raw_date = date_tag.text.strip()

        try:
            month, day = map(int, raw_date.split('/'))
            #print(f"month{month}, day{day}")
            if is_first_page and month != 1:
                continue
                # ✅ 最後一頁，遇到 1/1 → 代表 12/31 結束了，整頁不再繼續抓
            if is_last_page and month == 1 and day == 1:
                print("⚠️ 遇到 1/1，停止讀取此頁")
                break

            date_str = f"{month:02d}{day:02d}"  # 轉成 "MMDD"
        except:
            continue

        post = {
            'date': date_str,
            'title': title,
            'url': full_url
        }

        articles.append(post)

        if push_tag in ['爆'] or (push_tag.isdigit() and int(push_tag) >= 100):
            popular_articles.append(post)

    return soup


def detect_date_on_page(index):
    url = f"{PTT_URL}/bbs/{BOARD}/index{index}.html"
    res = session.get(url, timeout=5)
    if res.status_code != 200:
        print(f"❌ 無法讀取 index{index}")
        return []

    soup = BeautifulSoup(res.text, 'html.parser')
    entries = soup.select('div.r-ent')

    dates = []
    for entry in entries:
        date_tag = entry.select_one('div.date')
        if not date_tag:
            continue
        try:
            raw_date = date_tag.text.strip()
            month, day = map(int, raw_date.split('/'))
            dates.append(datetime(2023, month, day))
        except:
            continue
    return dates


def find_start_index():
    idx = 3371  #3371
    last_valid = None
    while idx > 3000:
        dates = detect_date_on_page(idx)
        if dates is None:
            print(f"⚠️ index{idx} 無法取得資料，跳過")
            idx -= 1
            continue

        print(f"🔍 檢查 index{idx}，找到日期們：{dates}")
        if any(d == datetime(2023, 1, 1) for d in dates):
            last_valid = idx  # 找到含 1/1 的頁面
        elif last_valid is not None:
            # 已經過了含 1/1 的最後一頁 → 停止往前找
            break

        idx -= 1
        time.sleep(random.uniform(0.3, 0.8))

    if last_valid is not None:
        print(f"✅ 找到第一頁含 2023/01/01 的 index：{last_valid}")
    else:
        print("❌ 沒找到含 2023/01/01 的頁面")
    return last_valid



def find_end_index():
    idx = 3647  #3647
    while idx < 4000:
        dates = detect_date_on_page(idx)
        print(f"🔍 檢查 index{idx}，找到日期們：{dates}")
        if any(d == datetime(2023, 12, 31) for d in dates):
            print(f"✅ 找到 2023/12/31 在 index{idx}")
            return idx
        idx -= 1
        time.sleep(random.uniform(0.3, 0.8))
    return None

def main():
    start_time = time.time()
    start_idx = find_start_index() #2023
    end_idx = find_end_index()   #2023

    print(f"✅ start_index = {start_idx}")
    print(f"✅ end_index = {end_idx}")
    #start_idx = 3657 #2024
    #end_idx = 3926 #2024
    
    for i in range(start_idx, end_idx + 1):
        print(f"\nCrawling index {i} ...")
        page_url = f"{PTT_URL}/bbs/{BOARD}/index{i}.html"
        is_first = (i == start_idx)
        is_last = (i == end_idx)
        soup = parse_index_page(page_url, is_first_page=is_first, is_last_page=is_last)
        if soup is None:
            continue
        sleep_time = random.uniform(0.5, 1.5)
        print(f"休息 {sleep_time:.2f} 秒避免被鎖 IP")
        time.sleep(sleep_time)

    with open("articles.jsonl", "w", encoding="utf-8") as f:
        for a in articles:
            json.dump(a, f, ensure_ascii=False)
            f.write("\n")

    with open("popular_articles.jsonl", "w", encoding="utf-8") as f:
        for a in popular_articles:
            json.dump(a, f, ensure_ascii=False)
            f.write("\n")

    end_time = time.time()
    duration = end_time - start_time
    print(f"\n⏱ 執行完畢！總耗時：{duration:.2f} 秒")
    print(f"\n爬蟲完成，共 {len(articles)} 篇文章，其中 {len(popular_articles)} 篇為熱門文章。")
    print("=== 前 5 篇文章 ===")
    for a in articles[:5]:
        print(a)
    print("=== 後 5 篇文章 ===")
    for a in articles[-5:]:
        print(a)

### 2. Push
def top10(counter):
    # 先把 Counter 轉成列表
    users = [{"user_id": u, "count": c} for u, c in counter.items()]
    # 先照 user_id 字典序大到小排（reverse 排 user_id）
    users.sort(key=lambda x: x["user_id"], reverse=True)
    # 再照 count 大到小排（穩定排序，保留前面字典序排序結果）
    users.sort(key=lambda x: x["count"], reverse=True)
    return users[:10]

def run_push_analysis(start_date, end_date):
    start_time = time.time()  # 計時開始
    start_date = int(start_date)
    end_date = int(end_date)

    with open("articles.jsonl", "r", encoding="utf-8") as f:
        articles_data = [json.loads(line) for line in f]

    filtered_articles = [
        a for a in articles_data
        if "date" in a and start_date <= int(a["date"]) <= end_date
    ]

    print(f"✅ 在 {start_date} 到 {end_date} 之間，共找到 {len(filtered_articles)} 篇文章")

    push_counter = Counter()
    boo_counter = Counter()
    push_total = 0
    boo_total = 0

    for idx, a in enumerate(filtered_articles):
        try:
            res = session.get(a["url"], timeout=5)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, 'html.parser')
            push_tags = soup.select("div.push")

            for tag in push_tags:
                tag_type = tag.select_one("span.push-tag")  # 例如 "推", "噓", "→"
                user_span = tag.select_one("span.push-userid") # 使用者 ID
                if not tag_type or not user_span:
                    continue

                tag_text = tag_type.text.strip()
                user = user_span.text.strip()

                if tag_text == "推":
                    push_counter[user] += 1
                    push_total += 1
                elif tag_text == "噓":
                    boo_counter[user] += 1
                    boo_total += 1

        except Exception as e:
            print(f"⚠️ 無法處理文章：{a['url']}，錯誤：{e}")
            continue

        if (idx + 1) % 10 == 0:
            sleep_time = random.uniform(1, 1.5)
            print(f"🛌 第 {idx+1} 篇，休息 {sleep_time:.2f} 秒")
            time.sleep(sleep_time)


    result = {
        "push": {
            "total": push_total,
            "top10": top10(push_counter)
        },
        "boo": {
            "total": boo_total,
            "top10": top10(boo_counter)
        }
    }

    output_filename = f"push_{start_date:04d}_{end_date:04d}.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"📁 已輸出結果至 {output_filename}")

    end_time = time.time()
    duration = end_time - start_time
    print(f"\n📁 已輸出結果至 {output_filename}")
    print(f"⏱️ 分析總耗時：{duration:.2f} 秒")


### 3. Popular 
def run_popular_analysis(start_date, end_date):
    start_time = time.time()
    start_date = int(start_date)
    end_date = int(end_date)

    with open("popular_articles.jsonl", "r", encoding="utf-8") as f:
        articles_data = [json.loads(line) for line in f]

    filtered_articles = [
        a for a in articles_data
        if "date" in a and start_date <= int(a["date"]) <= end_date
    ]

    print(f"✅ 在 {start_date} 到 {end_date} 之間，共找到 {len(filtered_articles)} 篇推爆文章")

    image_urls = []
    img_pattern = re.compile(r'https?://[^\s]+\.(?:jpg|jpeg|png|gif)', re.IGNORECASE)

    for idx, a in enumerate(filtered_articles):
        try:
            res = session.get(a["url"], timeout=5)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, 'html.parser')

            # 找內文文字
            main_content = soup.select_one("#main-content")
            if main_content:
                text = main_content.get_text()
                image_urls += img_pattern.findall(text)

            # 找留言文字
            push_tags = soup.select("div.push span.push-content")
            for tag in push_tags:
                image_urls += img_pattern.findall(tag.text)

            if (idx + 1) % 5 == 0:
                sleep_time = random.uniform(0.5, 1.5)
                print(f"🛌 已處理第 {idx+1} 篇，休息 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)

        except Exception as e:
            print(f"⚠️ 無法處理文章：{a['url']}，錯誤：{e}")
            continue
    
    ###############################################
    #image_urls = list(OrderedDict.fromkeys(image_urls))

    result = {
        "number_of_popular_articles": len(filtered_articles),
        "image_urls": image_urls
    }

    output_filename = f"popular_{start_date:04d}_{end_date:04d}.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"📁 已輸出結果至 {output_filename}")
    print(f"⏱️ 分析總耗時：{time.time() - start_time:.2f} 秒")


### 4. Keyword
def extract_valid_text(text):
    lines = text.split("\n")
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if start_idx is None and line.startswith("作者"):
            start_idx = i
        if line.startswith("※ 發信站"):
            end_idx = i
            break
    if start_idx is not None and end_idx is not None:
        return "\n".join(lines[start_idx:end_idx])
    else:
        return None

def run_keyword_analysis(start_date, end_date, keyword):
    start_time = time.time()
    start_date = int(start_date)
    end_date = int(end_date)

    with open("articles.jsonl", "r", encoding="utf-8") as f:
        articles_data = [json.loads(line) for line in f]

    filtered_articles = [
        a for a in articles_data
        if "date" in a and start_date <= int(a["date"]) <= end_date
    ]

    print(f"✅ 在 {start_date} 到 {end_date} 之間，共找到 {len(filtered_articles)} 篇文章")

    image_urls = []
    img_pattern = re.compile(r'https?://[^\s]+\.(?:jpg|jpeg|png|gif)', re.IGNORECASE)

    for idx, a in enumerate(filtered_articles):
        try:
            res = session.get(a["url"], timeout=5)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, 'html.parser')
            main_content = soup.select_one("#main-content")
            if main_content:
                text = main_content.get_text()
                valid_text = extract_valid_text(text)

                if valid_text and keyword in valid_text:
                    image_urls += img_pattern.findall(text)

                    push_tags = soup.select("div.push span.push-content")
                    for tag in push_tags:
                        image_urls += img_pattern.findall(tag.text)

            if (idx + 1) % 5 == 0:
                sleep_time = random.uniform(0.5, 1.5)
                print(f"🛌 已處理第 {idx+1} 篇，休息 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)

        except Exception as e:
            print(f"⚠️ 無法處理文章：{a['url']}，錯誤：{e}")
            continue
    
    ###############################################
    #image_urls = list(OrderedDict.fromkeys(image_urls))

    result = {
        "image_urls": image_urls
    }

    output_filename = f"keyword_{start_date:04d}_{end_date:04d}_{keyword}.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"📁 已輸出結果至 {output_filename}")
    print(f"⏱️ 分析總耗時：{time.time() - start_time:.2f} 秒")



if __name__ == "__main__":
    if len(sys.argv) >= 2:
        if sys.argv[1] == "crawl":
            main()
        elif sys.argv[1] == "push" and len(sys.argv) == 4:
            run_push_analysis(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "popular" and len(sys.argv) == 4:
            run_popular_analysis(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "keyword" and len(sys.argv) == 5:
            run_keyword_analysis(sys.argv[2], sys.argv[3],sys.argv[4])
        else:
            print("指令錯誤，請使用：")
            print("  python 313657003.py crawl")
            print("  python 313657003.py push {start_date} {end_date}")
            print("  python 313657003.py popular {start_date} {end_date}")
            print("  python 313657003.py keyword {start_date} {end_date} {keyword}")

    else:
        print("請輸入正確指令，例如：python 313657003.py crawl 或 push")


