# PTT Beauty Board Crawling in 2023/2024
---
Project: PTT Beauty Board Crawling in 2023/2024

Author: CHOU CHIA HSUAN

Date: 2024-05-05

Course: Generative AI

---

# 1. Crawl – Article Collection

**Goal:** Collect all valid articles from 2024 and identify "popular" ones.

**Details:**
- Only articles from January 1 to December 31, 2024 are included.
- Articles with [公告] or Fw:[公告] in the title are excluded.
- Articles are saved to articles.jsonl, and popular articles (push count ≥ 100 or "爆") are stored in popular_articles.jsonl.
- Each article record contains:  
  {"date": "MMDD", "title": "...", "url": "https://..."}

**Run:**
```bash
python 2024.py crawl
```

# 2. Push – Push/ Boo Analysis
**Goal:** Analyze user push (推) and boo (噓) behavior(from articles.jsonl).

**Details:**

- Input: Start and end dates (MMDD) as arguments.

- Outputs the total number of pushes and boos 

- Generates Top10 pushers and Top10 booers, sorted by:

    1. Descending by count.

    2. Lexicographically by user ID if counts are tied.

Output file: push_{start}_{end}.json

**Run:**
```bash
python 2024.py push 0101 0331
```

# 3. Popular – Popular Article Image Extraction
**Goal:** Extract all image URLs shared in popular articles (from popular_articles.jsonl).

**Details:**

- Image URLs are matched by regex: http(s)://... .(jpg|jpeg|png|gif)

- Searches both the article content and comment section.

- Output file: popular_{start}_{end}.json

**Run:**
```bash
python 2024.py popular 0101 0331
```

# 4. Keyword – Keyword-Based Image Search
**Goal:** Find all articles containing a specific keyword and extract related image URLs.(from articles.jsonl).

**Details:**
- Searches keyword only within the article body (from "作者" to "※ 發信站").

- Includes images from both the article and comment section.

- Output file: keyword_{start}_{end}_{keyword}.json

**Run:**
```bash
python 2024.py keyword 0101 0331 IG
```
