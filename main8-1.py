import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
import html
import os
from google import genai
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. API 키 및 설정 ---
# ==========================================
# 🚨 본인의 API 키로 모두 교체해 주세요!
GEMINI_API_KEY = "AI어쩌구api키입력"
NAVER_CLIENT_ID = "WR6Xdx네이버api"
NAVER_CLIENT_SECRET = "네이버api비번"

SEARCH_QUERY = "적재적소 인력배치 사례"
EXCEL_FILENAME = "Workforce_Allocation_Cases.xlsx"


# ==========================================
# --- 2. 뉴스 크롤링 함수 ---
# ==========================================
def clean_html_text(text):
    """HTML 태그 제거 및 특수문자 디코딩"""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def get_naver_news(query, display=15):
    """네이버 뉴스 검색 API 크롤링 (제목 + 요약)"""
    print("📰 네이버 뉴스를 수집 중입니다...")
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {"query": query, "display": display, "sort": "sim"}

    articles = []
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            items = response.json().get('items', [])
            for item in items:
                title = clean_html_text(item['title'])
                description = clean_html_text(item['description'])
                articles.append(f"[네이버 뉴스] 제목: {title}\n내용 요약: {description}")
        else:
            print(f"❌ 네이버 API 에러: 상태 코드 {response.status_code}")
    except Exception as e:
        print(f"❌ 네이버 뉴스 수집 중 오류: {e}")

    return articles


def get_google_news(query):
    """구글 뉴스 RSS 크롤링 (제목 + 요약)"""
    print("📰 구글 뉴스를 수집 중입니다...")
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    articles = []
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # lxml parser를 명시적으로 사용하도록 수정
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item', limit=15)
            for item in items:
                title = clean_html_text(item.title.text)
                description = clean_html_text(item.description.text) if item.description else ""
                articles.append(f"[구글 뉴스] 제목: {title}\n내용 요약: {description}")
        else:
            print(f"❌ 구글 RSS 에러: 상태 코드 {response.status_code}")
    except Exception as e:
        print(f"❌ 구글 뉴스 수집 중 오류: {e}")

    return articles


# ==========================================
# --- 3. Gemini API 연동 및 엑셀 저장 ---
# ==========================================
def main():
    print("=" * 60)
    print("🚀 '적재적소 인력배치' 뉴스 스크래핑 및 AI 분석 시작")
    print("=" * 60)

    # 1. 크롤링 실행
    naver_data = get_naver_news(SEARCH_QUERY)
    google_data = get_google_news(SEARCH_QUERY)

    all_articles = naver_data + google_data
    all_news_text = "\n\n".join(all_articles)

    if not all_articles:
        print("❌ 수집된 뉴스 데이터가 없습니다. 검색어나 API 설정을 확인해주세요.")
        return

    print(f"✅ 총 {len(all_articles)}건의 뉴스 기사(요약)를 수집했습니다.")

    # 2. Gemini API 호출
    print("\n🤖 Gemini 2.5 Flash 모델이 데이터를 분석하고 사례를 추출 중입니다...")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        prompt = f"""
        당신은 기업의 인적자원관리(HR) 및 피플애널리틱스 전문가입니다.
        아래 수집된 뉴스 기사 데이터를 분석하여, 기업이나 기관의 '적재적소 인력배치(Optimal Workforce Allocation)' 성공 사례를 추출해 주세요.

        반드시 아래의 JSON 배열(Array) 형식으로만 응답해야 하며, 마크다운 코드 블록(```json ... ```) 안에 담아주세요.
        다른 부연 설명은 절대 하지 마세요. 중복되는 사례는 하나로 합치고, 내용이 모호한 기사는 제외하세요.

        [JSON 출력 형식]
        [
          {{
            "조직명": "기업 또는 기관 이름",
            "인력배치_사례_요약": "어떤 방식으로 적재적소에 인력을 배치했는지에 대한 구체적 설명",
            "기대효과_및_성과": "이를 통해 얻은 성과나 긍정적 효과"
          }}
        ]

        [뉴스 데이터]
        {all_news_text}
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )

        # 3. JSON 파싱
        result_text = response.text.strip()
        json_match = re.search(r'\[.*\]', result_text, re.DOTALL)

        if json_match:
            cases_json = json_match.group()
            cases_list = json.loads(cases_json)

            # 4. DataFrame 변환 및 엑셀 저장
            if len(cases_list) > 0:
                df = pd.DataFrame(cases_list)

                # 🚨 에러 해결: encoding 옵션 제거
                df.to_excel(EXCEL_FILENAME, index=False)

                print("\n" + "=" * 60)
                print(f"🎉 분석 완료! 총 {len(cases_list)}개의 유의미한 사례가 추출되었습니다.")
                print("-" * 60)
                for idx, case in enumerate(cases_list, 1):
                    org_name = case.get('조직명', '알수없음')
                    print(f"{idx}. {org_name}")
                print("=" * 60)

                full_path = os.path.abspath(EXCEL_FILENAME)
                print(f"💾 추출된 사례가 엑셀 파일로 저장되었습니다.\n경로: {full_path}")
            else:
                print("⚠️ 수집된 뉴스 중에서 적합한 인력배치 사례를 찾지 못했습니다.")

        else:
            print("❌ AI 응답에서 올바른 JSON 형식을 찾지 못했습니다.\n[원문 응답]\n", result_text)

    except Exception as e:
        print(f"\n❌ Gemini API 호출 또는 데이터 처리 중 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    main()