import feedparser
import csv
import os
import urllib.parse  # URL 인코딩을 위해 추가된 라이브러리
from datetime import datetime


def crawl_google_news_to_csv(keyword):
    # 1. 키워드 URL 인코딩 (띄어쓰기 등을 안전한 문자로 변환)
    encoded_keyword = urllib.parse.quote(keyword)

    # 인코딩된 키워드를 URL에 삽입
    rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"

    # 2. feedparser로 RSS 데이터 파싱
    print(f"[{keyword}] 키워드로 뉴스를 검색 중입니다...")
    feed = feedparser.parse(rss_url)

    # 3. 저장 경로 및 파일명 설정
    save_dir = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#2"
    os.makedirs(save_dir, exist_ok=True)

    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"GoogleNews_{keyword.replace(' ', '')}_{current_time}.csv"  # 파일명에서도 빈칸 제거
    file_path = os.path.join(save_dir, file_name)

    # 4. CSV 파일로 저장
    with open(file_path, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['제목', '기사 링크', '출판일'])

        for entry in feed.entries:
            title = entry.title
            link = entry.link
            published = entry.published
            writer.writerow([title, link, published])

    print(f"✅ 스크래핑 완료! 파일이 성공적으로 저장되었습니다.\n📁 저장 위치: {file_path}")


# 코드 실행
if __name__ == "__main__":
    search_keyword = "조용한 사직"
    crawl_google_news_to_csv(search_keyword)