import feedparser
import csv
import os
from datetime import datetime


def crawl_google_news_to_csv(keyword):
    # 1. Google News RSS URL 설정 (한국어 설정 포함)
    rss_url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"

    # 2. feedparser로 RSS 데이터 파싱
    print(f"[{keyword}] 키워드로 뉴스를 검색 중입니다...")
    feed = feedparser.parse(rss_url)

    # 3. 저장 경로 및 파일명 설정
    # 경로에 백슬래시(\)가 포함되어 있으므로 r(Raw String)을 사용하여 이스케이프 문자 오류 방지
    save_dir = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#1"

    # 폴더가 존재하지 않으면 자동으로 생성
    os.makedirs(save_dir, exist_ok=True)

    # 파일명에 현재 시간을 추가하여 덮어쓰기 방지
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"GoogleNews_{keyword}_{current_time}.csv"
    file_path = os.path.join(save_dir, file_name)

    # 4. CSV 파일로 저장
    # utf-8-sig 인코딩: 엑셀에서 파일을 열 때 한글이 깨지는 것을 방지
    with open(file_path, mode='w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)

        # CSV 헤더(첫 줄) 작성
        writer.writerow(['제목', '기사 링크', '출판일'])

        # 파싱된 뉴스 기사 목록을 순회하며 데이터 추출
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            published = entry.published

            # 행 단위로 데이터 저장
            writer.writerow([title, link, published])

    print(f"✅ 스크래핑 완료! 파일이 성공적으로 저장되었습니다.\n📁 저장 위치: {file_path}")


# 코드 실행
if __name__ == "__main__":
    # 검색하고 싶은 키워드를 입력하세요
    search_keyword = "인공지능"
    crawl_google_news_to_csv(search_keyword)