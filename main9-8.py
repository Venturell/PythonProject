import pandas as pd
import json
import re
import time
import os
from google import genai
from google.genai import types
import warnings

warnings.filterwarnings('ignore')

#회사리뷰 데이터로부터 감정분석 Gemini
# ==========================================
# 1. API 키 및 환경 설정
# ==========================================
# 🚨 여기에 Google AI Studio에서 발급받은 API 키를 입력하세요!
API_KEY = "AI어쩌구api입력하세요"
MODEL_NAME = 'gemini-2.5-flash'

csv_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#9\9_PAproject_9_4_sentiment.csv"
output_path = os.path.join(os.path.dirname(csv_path), "9_PAproject_9_4_GenAI_sentiment_result.csv")


# ==========================================
# 2. 다단계 JSON 파싱 함수
# ==========================================
def parse_json_response(response_text):
    """Gemini 응답에서 JSON 배열을 안전하게 추출하는 다단계 파싱 로직"""
    # 1단계: 기본 JSON 로드 시도
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass  # 실패 시 2단계로 이동

    # 2단계: 정규표현식을 활용하여 마크다운 블록(```json ... ```) 또는 배열([...]) 영역만 강제 추출
    try:
        # 대괄호 [ 로 시작해서 ] 로 끝나는 모든 문자열 추출 (줄바꿈 포함)
        match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if match:
            extracted_json = match.group(0)
            return json.loads(extracted_json)
    except Exception as e:
        print(f"❌ [에러] 다단계 파싱 실패. 원본 응답 확인 필요: {e}")

    return None  # 모두 실패 시 None 반환


# ==========================================
# 3. 데이터 로드 및 배치(Batch) 준비
# ==========================================
print("데이터를 불러오고 감정 분석을 준비합니다...\n")
# Windows 환경을 고려한 한글 인코딩 처리
try:
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
except UnicodeDecodeError:
    df = pd.read_csv(csv_path, encoding='cp949')

# 고유 ID 부여 (배치 처리 후 원본 데이터와 순서를 정확히 매핑하기 위함)
df['temp_id'] = range(len(df))
reviews = df[['temp_id', 'review']].dropna().to_dict('records')

BATCH_SIZE = 30
total_batches = (len(reviews) // BATCH_SIZE) + (1 if len(reviews) % BATCH_SIZE != 0 else 0)

print(f"총 {len(reviews)}개의 리뷰를 {BATCH_SIZE}개씩 묶어 총 {total_batches}번의 API 호출로 분석합니다.")

# ==========================================
# 4. Gemini API 감정 분석 수행 (Batch Processing)
# ==========================================
client = genai.Client(api_key=API_KEY)
all_results = []

for i in range(total_batches):
    batch = reviews[i * BATCH_SIZE: (i + 1) * BATCH_SIZE]

    # 배치 데이터를 프롬프트용 텍스트로 변환 (ID와 리뷰 내용 포함)
    batch_text = "\n".join([f"ID: {item['temp_id']} | Review: {item['review']}" for item in batch])

    prompt = f"""
    당신은 기업의 인적자원(HR) 및 감정 분석 전문가입니다.
    다음 제공된 직원들의 리뷰 데이터를 읽고, 각 리뷰에 대해 7가지 감정(분노, 행복, 불안, 당황, 슬픔, 상처, 중립)의 점수(0~100점)와 최종 대표 감정, 그리고 그렇게 판단한 이유를 분석해 주세요.

    반드시 아래와 같은 JSON 배열(Array of Objects) 형식으로만 응답해야 합니다.

    [출력 형식 예시]
    [
      {{
        "temp_id": 0,
        "score_분노": 10,
        "score_행복": 0,
        "score_불안": 80,
        "score_당황": 10,
        "score_슬픔": 0,
        "score_상처": 0,
        "score_중립": 0,
        "final_emotion": "불안",
        "reason": "업무 성과에 대한 막연한 걱정과 초조함이 텍스트에서 명확히 드러남"
      }}
    ]

    [분석할 데이터]
    {batch_text}
    """

    try:
        # response_mime_type을 통한 JSON 강제 출력 설정
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )

        # 다단계 파싱 로직 적용
        parsed_batch = parse_json_response(response.text)

        if parsed_batch:
            all_results.extend(parsed_batch)
            print(f"✅ Batch {i + 1}/{total_batches} 완료 ({len(parsed_batch)}건 처리)")
        else:
            print(f"⚠️ Batch {i + 1}/{total_batches} 파싱 실패. 해당 배치는 누락됩니다.")

    except Exception as e:
        print(f"❌ Batch {i + 1}/{total_batches} API 호출 에러: {e}")

    # API 속도 제한 방지를 위한 대기 시간 (마지막 배치는 제외)
    if i < total_batches - 1:
        time.sleep(1)

# ==========================================
# 5. 결과 통합 및 엑셀 저장
# ==========================================
# 추출된 JSON 리스트를 데이터프레임으로 변환
result_df = pd.DataFrame(all_results)

# 원본 데이터와 temp_id를 기준으로 병합 (Left Join)
if not result_df.empty:
    df_final = pd.merge(df, result_df, on='temp_id', how='left')
    df_final = df_final.drop(columns=['temp_id'])  # 임시 ID 삭제

    # 윈도우 환경 한글 깨짐 방지를 위한 utf-8-sig 인코딩
    df_final.to_csv(output_path, index=False, encoding='utf-8-sig')
else:
    print("\n❌ 추출된 결과가 없어 파일을 저장하지 못했습니다.")
    exit()

# ==========================================
# 6. 감정 분포 요약 통계 출력
# ==========================================
print("\n" + "=" * 60)
print("💡 [Gemini API 기반 리뷰 감정 분포 요약 통계]")
print("=" * 60)

# 최종 감정 라벨이 존재하는 데이터만 집계
valid_emotions = df_final['final_emotion'].dropna()
emotion_counts = valid_emotions.value_counts()
emotion_ratios = valid_emotions.value_counts(normalize=True) * 100

summary_df = pd.DataFrame({
    '감정 (Emotion)': emotion_counts.index,
    '빈도수 (Count)': emotion_counts.values,
    '비율 (%)': emotion_ratios.values.round(2)
})

print(summary_df.to_string(index=False))
print("-" * 60)
print(f"✅ 분석 완료! 전체 세부 결과 및 판단 사유가 CSV로 저장되었습니다.\n저장 경로: {output_path}")