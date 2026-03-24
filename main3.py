import requests
import pandas as pd
import re
import os

# 1. 네이버 API 인증 정보 (직접 발급받은 키를 입력해야 합니다)
client_id = "fJtr2bCj0EFAk2Roce6k"
client_secret = "SUJ9QQzZFK"

# 2. 검색어 및 요청 URL 설정
query = "성과급"
url = "https://openapi.naver.com/v1/search/news.json"

params = {
    "query": query,
    "display": 30,
    "start": 1,
    "sort": "date"
}

headers = {
    "X-Naver-Client-Id": client_id,
    "X-Naver-Client-Secret": client_secret
}


def clean_html(text):
    """API 결과에 포함된 HTML 태그(<b> 등)를 깔끔하게 제거하는 함수"""
    text = re.sub(r'<.*?>', '', text)
    text = text.replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    return text


# 3. 새로운 저장 경로 설정 및 폴더 생성
save_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3"
file_name = "네이버뉴스_성과급_검색결과.xlsx"
file_path = os.path.join(save_path, file_name)

if not os.path.exists(save_path):
    os.makedirs(save_path)
    print(f"저장 폴더가 존재하지 않아 새로 생성했습니다:\n{save_path}")

print(f"'{query}' 관련 뉴스를 네이버 API로 검색 중입니다...")

# 4. API 요청 및 데이터 파싱
response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    items = data.get('items', [])

    news_list = []
    for item in items:
        news_list.append({
            "제목": clean_html(item['title']),
            "링크": item['link'],
            "요약": clean_html(item['description']),
            "발행일": item['pubDate']
        })

    # 5. 데이터프레임 변환 및 지정된 경로에 엑셀 저장
    df = pd.DataFrame(news_list)
    df.to_excel(file_path, index=False)

    print(f"\n🎉 성공적으로 30개의 기사를 가져왔습니다!")
    print(f"파일이 아래 경로에 저장되었습니다:\n{file_path}")

else:
    print(f"Error Code: {response.status_code}")
    print("API 요청에 실패했습니다. Client ID와 Secret이 정확한지 다시 확인해 주세요.")