import pandas as pd
from google import genai
import time
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. API 키 및 모델 설정 ---
# ==========================================
# 🚨 여기에 Google AI Studio에서 발급받은 API 키를 입력하세요!
API_KEY = "AIzAPI키입력어쩌구야르"
client = genai.Client(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash'

# ==========================================
# --- 2. 파일 경로 설정 ---
# ==========================================
# 입력 파일 경로
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_2_log.xlsx"
# 출력 파일 경로 (기존 파일명에 _classified 추가)
output_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_2_log_classified.xlsx"

print("엑셀 데이터를 불러오고 있습니다...")
df = pd.read_excel(file_path)


# ==========================================
# --- 3. AI 텍스트 분류 함수 정의 ---
# ==========================================
def classify_message(text):
    """주어진 문장을 3가지 카테고리 중 하나로 분류하는 함수"""
    # 결측치(빈칸) 처리
    if pd.isna(text) or str(text).strip() == "":
        return "empty"

    # AI에게 역할과 명확한 분류 기준(가이드라인)을 부여
    prompt = f"""
    당신은 기업의 사내 소통을 분석하는 피플애널리틱스 전문가입니다.
    아래 [메신저 대화 내용]을 읽고, 다음 3가지 카테고리 중 가장 적합한 것 '하나만' 선택하세요.
    다른 부연 설명이나 특수기호 없이 오직 영어 소문자 단어(advice, communication, collaboration) 하나만 출력해야 합니다.

    [분류 기준]
    1. advice: 업무적 조언, 멘토링, 피드백 제공 및 요청, 문제 해결을 위한 질문과 답변
    2. communication: 단순 정보 공유, 일상적인 대화, 안부 인사, 단순 공지, 감정 교류
    3. collaboration: 공동 작업 진행, 회의 일정 조율, 업무 협업 및 역할 분담, 산출물 공유 및 취합

    [메신저 대화 내용]
    "{text}"
    """

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        # 반환된 텍스트 정리 (공백 제거, 소문자 변환)
        result = response.text.strip().lower()

        # AI가 부연 설명을 붙였을 경우를 대비한 안전장치 (원하는 단어만 추출)
        for valid_category in ["advice", "communication", "collaboration"]:
            if valid_category in result:
                return valid_category

        return "unclassified"  # 3개 중 아무것도 매칭되지 않았을 때

    except Exception as e:
        print(f"오류 발생: {e}")
        return "error"


# ==========================================
# --- 4. 데이터 분류 실행 ---
# ==========================================
print(f"총 {len(df)}건의 대화 내용 분류를 시작합니다. (데이터 양에 따라 시간이 소요될 수 있습니다.)")
print("-" * 60)

categories = []

for index, row in df.iterrows():
    log_text = row['log']  # 'log' 컬럼의 데이터 추출
    category = classify_message(log_text)
    categories.append(category)

    # 진행 상황 출력 (10건 단위)
    if (index + 1) % 10 == 0 or (index + 1) == len(df):
        print(f"  -> {index + 1} / {len(df)}건 분류 완료...")

    # API 요청 제한(Rate Limit)을 피하기 위한 미세한 대기 시간
    time.sleep(0.5)

# 예측된 결과를 새로운 컬럼으로 추가
df['message_type'] = categories

# ==========================================
# --- 5. 결과 저장 및 요약 출력 ---
# ==========================================
df.to_excel(output_path, index=False)

print("-" * 60)
print("✅ AI 분류 작업이 모두 완료되었습니다!")
print(f"💾 저장 경로: {output_path}\n")

# 최종 분류 결과 요약 통계 보여주기
print("[분류 결과 요약]")
print(df['message_type'].value_counts())