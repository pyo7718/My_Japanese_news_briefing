import feedparser
import requests
import deepl
import time
import re
import html
import os
from datetime import datetime
from urllib.parse import quote

# GitHub Secrets에서 정보를 가져옵니다.
DEEPL_AUTH_KEY = os.environ.get("DEEPL_AUTH_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

TOPICS = [
    "半導体 OR ロボット",
    "日本 経済指標 OR 金利 OR 物価",
    "注目 ビジネス OR 有望 産業",
    "社会 人気"
]

EXCLUDE_SOURCES = ["joongang", "chosun", "yonhap", "hani", "donga", "kbs", "seoul economy"]

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def translate_text(text):
    if not text or not DEEPL_AUTH_KEY: return text
    try:
        translator = deepl.Translator(DEEPL_AUTH_KEY)
        result = translator.translate_text(text, target_lang="KO")
        return result.text
    except Exception as e:
        print(f"번역 오류: {e}")
        return text

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": text, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, json=payload)
        return r.status_code
    except Exception as e:
        print(f"전송 오류: {e}")
        return 500

def fetch_japanese_news():
    all_entries = []
    for topic in TOPICS:
        encoded_topic = quote(topic)
        rss_url = f"https://news.google.com/rss/search?q={encoded_topic}+when:24h&hl=ja&gl=JP&ceid=JP:ja"
        feed = feedparser.parse(rss_url)
        all_entries.extend(feed.entries)

    unique_news = []
    seen_links = set()
    for e in all_entries:
        source_name = e.source.get('title', '').lower()
        link = e.link.lower()
        if any(ex in source_name or ex in link for ex in EXCLUDE_SOURCES):
            continue
        if link not in seen_links:
            is_major = any(m in source_name for m in ['nhk', 'yahoo', 'nikkei', 'asahi', 'yomiuri'])
            unique_news.append({'entry': e, 'priority': 0 if is_major else 1})
            seen_links.add(link)
    
    unique_news.sort(key=lambda x: x['priority'])
    return [x['entry'] for x in unique_news[:10]]

def main():
    news_list = fetch_japanese_news()
    if not news_list: return

    full_message = f"<b>📅 {datetime.now().strftime('%Y-%m-%d')} 일본 뉴스 브리핑</b>\n"
    full_message += "━━━━━━━━━━━━━━━━━━\n\n"

    for i, entry in enumerate(news_list):
        title_ko = translate_text(entry.title)
        summary_ko = translate_text(clean_html(entry.summary)[:150])
        
        # 파파고 웹번역 링크 사용 (더 안정적)
        web_trans_link = f"https://papago.naver.net/website?locale=ko&source=ja&target=ko&url={quote(entry.link)}"
        
        full_message += f"<b>{i+1}. {html.escape(title_ko)}</b>\n"
        full_message += f"📝 {html.escape(summary_ko)}...\n"
        full_message += f"🔗 <a href='{entry.link}'>[원문]</a> | 🌐 <a href='{web_trans_link}'>[번역]</a>\n\n"

    send_telegram(full_message)

if __name__ == "__main__":
    main()
