import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. 파일 경로 설정
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#9\9_PAproject_9_5_detect.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "9_PAproject_9_5_detect_result.xlsx")

print("데이터를 불러오고 모델 학습을 준비 중입니다...\n")

# ==========================================
# 2. 데이터 로드 및 전처리 (Train Data 구성)
# ==========================================
# 각 시트에서 데이터 불러오기
df_A = pd.read_excel(file_path, sheet_name='A')
df_B = pd.read_excel(file_path, sheet_name='B')
df_mixed = pd.read_excel(file_path, sheet_name='Mixed')

# 정답 라벨(Label) 부여
df_A['Author'] = 'A'
df_B['Author'] = 'B'

# A와 B의 데이터를 합쳐서 학습용(Training) 데이터셋 생성
df_train = pd.concat([df_A, df_B], ignore_index=True)

# 결측치(비어있는 텍스트) 제거
df_train = df_train.dropna(subset=['text']).reset_index(drop=True)
df_mixed = df_mixed.dropna(subset=['text']).reset_index(drop=True)

print(f"학습 데이터(Train): A 작성 글 {len(df_A)}건, B 작성 글 {len(df_B)}건")
print(f"예측 대상(Mixed): {len(df_mixed)}건\n")

# ==========================================
# 3. TF-IDF 벡터화 (텍스트 -> 숫자 변환)
# ==========================================
# 단어의 빈도와 희귀성을 고려하여 텍스트를 수치화하는 TF-IDF 초기화
vectorizer = TfidfVectorizer(max_features=5000) # 최대 5000개의 주요 단어 기준

# 학습 데이터로 단어 사전(Vocabulary) 구축 및 변환
X_train = vectorizer.fit_transform(df_train['text'])
y_train = df_train['Author']

# 익명 글(Mixed) 데이터 변환 (fit_transform이 아닌 transform 사용!)
X_test = vectorizer.transform(df_mixed['text'])

# ==========================================
# 4. 로지스틱 회귀(Logistic Regression) 모델 학습 및 예측
# ==========================================
print("로지스틱 회귀 모델을 학습하고 작성자를 예측합니다...\n")

# 모델 초기화 및 학습
model = LogisticRegression(random_state=42)
model.fit(X_train, y_train)

# Mixed 시트의 작성자 예측
predictions = model.predict(X_test)

# 단순 결과뿐만 아니라 A일 확률, B일 확률도 함께 계산 (분석의 신뢰도를 위해)
probabilities = model.predict_proba(X_test)
classes = model.classes_ # ['A', 'B'] 순서 확인

# ==========================================
# 5. 결과 저장 및 요약
# ==========================================
# 예측 결과와 확률을 데이터프레임에 추가
df_mixed['Predicted_Author'] = predictions
for i, author_class in enumerate(classes):
    df_mixed[f'Prob_{author_class}(%)'] = (probabilities[:, i] * 100).round(2)

# 결과를 엑셀 파일로 저장
df_mixed.to_excel(output_path, index=False)

# 요약 통계 출력
print("=" * 50)
print("💡 [작성자 예측 결과 요약]")
print("=" * 50)
pred_counts = df_mixed['Predicted_Author'].value_counts()
for author, count in pred_counts.items():
    print(f" - {author} 작성자로 예측된 글: {count}건")

print("-" * 50)
print(f"✅ 예측이 완료되었습니다. 세부 확률 및 결과가 엑셀로 저장되었습니다.")
print(f"저장 경로: {output_path}")