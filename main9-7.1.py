import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. 파일 경로 및 환경 설정
# ==========================================
csv_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#9\9_PAproject_9_4_sentiment.csv"
output_path = os.path.join(os.path.dirname(csv_path), "9_PAproject_9_4_FinBERT_result.csv")

# KR-FinBert-SC 모델의 출력 라벨 (0: 부정, 1: 중립, 2: 긍정)
sentiment_labels = ['부정', '중립', '긍정']

print("데이터를 불러오고 KR-FinBert-SC 모델을 준비 중입니다...\n")

# GPU 사용 가능 여부 확인
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"현재 사용 중인 디바이스: {device}")

# ==========================================
# 2. 모델 및 토크나이저 로드 (Hugging Face)
# ==========================================
model_name = "snunlp/KR-FinBert-SC"

# AutoTokenizer와 AutoModel 사용
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
model.to(device)
model.eval()  # 평가 모드로 전환

# ==========================================
# 3. 데이터 로드 및 분석 수행
# ==========================================
# 데이터 불러오기 (한글 인코딩 에러 대비 utf-8, cp949 시도)
try:
    df = pd.read_csv(csv_path, encoding='utf-8')
except UnicodeDecodeError:
    df = pd.read_csv(csv_path, encoding='cp949')

# 결측치 제거 및 리스트 변환
reviews = df['review'].dropna().tolist()
print(f"\n총 {len(reviews)}개의 리뷰 데이터 감성 분석을 시작합니다. (부정/중립/긍정 분류)")

results = []
count = 0

with torch.no_grad():  # 예측 시에는 기울기 계산 불필요
    for text in reviews:
        # 1. 텍스트 토큰화 및 텐서 변환
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=128,
            padding="max_length"
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # 2. 모델 예측
        outputs = model(**inputs)
        logits = outputs.logits

        # 3. Softmax를 통과시켜 각 감성별 확률(점수) 도출
        probs = F.softmax(logits, dim=1).squeeze().cpu().numpy()

        # 4. 가장 높은 확률을 가진 감성(Top-1) 추출
        max_idx = probs.argmax()
        top_sentiment = sentiment_labels[max_idx]

        # 5. 결과 저장 (원문, 감성별 확률, 최종 라벨)
        row_data = {'review': text, 'final_sentiment': top_sentiment}
        for i, label in enumerate(sentiment_labels):
            row_data[f'score_{label}'] = round(probs[i] * 100, 2)  # 퍼센트 단위

        results.append(row_data)

        count += 1
        if count % 100 == 0 or count == len(reviews):
            print(f"  -> {count} / {len(reviews)}건 완료...")

# ==========================================
# 4. 결과 통합 및 저장
# ==========================================
# 분석 결과를 데이터프레임으로 변환
result_df = pd.DataFrame(results)

# 원본 데이터와 병합
df_final = pd.concat([df.reset_index(drop=True), result_df.drop(columns=['review'])], axis=1)

# CSV로 저장 (저장 파일명도 알기 쉽게 FinBERT_result로 변경했습니다)
df_final.to_csv(output_path, index=False, encoding='utf-8-sig')

# ==========================================
# 5. 요약 통계 출력
# ==========================================
print("\n" + "=" * 60)
print("💡 [KR-FinBert-SC 감성 분포 요약 통계]")
print("=" * 60)

sentiment_counts = df_final['final_sentiment'].value_counts()
sentiment_ratios = df_final['final_sentiment'].value_counts(normalize=True) * 100

summary_df = pd.DataFrame({
    '감성 (Sentiment)': sentiment_counts.index,
    '빈도수 (Count)': sentiment_counts.values,
    '비율 (%)': sentiment_ratios.values.round(2)
})

print(summary_df.to_string(index=False))
print("-" * 60)
print(f"✅ 분석 완료! 전체 세부 결과가 CSV로 저장되었습니다.\n저장 경로: {output_path}")    