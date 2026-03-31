import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import platform
import warnings

warnings.filterwarnings('ignore')  # 분석에 지장 없는 경고 메시지 숨김

# 머신러닝 및 평가 라이브러리
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

# SHAP (설명 가능한 AI) 라이브러리
import shap

# --- 0. 한글 폰트 설정 (Windows/맑은 고딕) ---
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# --- 1. 데이터 로드 (cp949 인코딩) ---
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3\3_PAproject_3_3_NPS.csv"

print("데이터를 불러오고 전처리를 진행합니다...")
df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

# --- 2. 데이터 필터링 및 연봉 계산 ---
# 정상 가입(1) & 200명 이상 대기업 필터링
df_filtered = df[(df['사업장가입상태코드'] == 1) & (df['가입자수'] >= 200)].copy()

# 숫자형 변환 및 연봉 산출 (연봉 = (인당고지금액 / 0.095) * 12)
df_filtered['당월고지금액'] = pd.to_numeric(df_filtered['당월고지금액'], errors='coerce')
df_filtered['가입자수'] = pd.to_numeric(df_filtered['가입자수'], errors='coerce')
df_filtered['연봉'] = (df_filtered['당월고지금액'] / df_filtered['가입자수'] / 0.095) * 12

# 적용일자에서 연도(업력) 추출
df_filtered['적용일자'] = pd.to_datetime(df_filtered['적용일자'], format='%Y-%m-%d', errors='coerce')
df_filtered['연도'] = df_filtered['적용일자'].dt.year

# --- 3. 타겟 산업 및 지역 필터링 ---
target_industry = [722000, 551001, 671202, 724000]
target_region = [41, 11, 28, 52]

df_filtered['사업장업종코드'] = pd.to_numeric(df_filtered['사업장업종코드'], errors='coerce')
df_filtered['법정동주소광역시도코드'] = pd.to_numeric(df_filtered['법정동주소광역시도코드'], errors='coerce')

df_final = df_filtered[(df_filtered['사업장업종코드'].isin(target_industry)) &
                       (df_filtered['법정동주소광역시도코드'].isin(target_region))].copy()

# 분석에 사용할 최종 변수 정제
df_final = df_final[['연봉', '가입자수', '연도', '사업장업종코드', '법정동주소광역시도코드']].dropna()

# --- 4. 더미 코딩 (범주형 변수 처리) ---
df_final['사업장업종코드'] = df_final['사업장업종코드'].astype(int).astype(str)
df_final['법정동주소광역시도코드'] = df_final['법정동주소광역시도코드'].astype(int).astype(str)

df_dummy = pd.get_dummies(df_final, columns=['사업장업종코드', '법정동주소광역시도코드'], drop_first=True, dtype=int)

# 독립변수(X)와 종속변수(y) 분할 후 학습/테스트 셋 분리
X = df_dummy.drop('연봉', axis=1)
y = df_dummy['연봉']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- 5. 모델 학습 및 비교 (RF, XGB, LGBM) ---
models = {
    'Random Forest': RandomForestRegressor(random_state=42),
    'XGBoost': XGBRegressor(random_state=42),
    'LightGBM': LGBMRegressor(random_state=42, min_child_samples=5, verbose=-1)  # 데이터 규모에 맞춰 파라미터 조정
}

print("\n" + "=" * 50)
print(f"{'Model':<15} | {'R2 Score':<10} | {'RMSE (만원)':<10}")
print("-" * 50)

best_r2 = -np.inf
best_model_name = ""

for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred)) / 10000

    print(f"{name:<15} | {r2:<10.4f} | {rmse:<10.0f}")

    if r2 > best_r2:
        best_r2 = r2
        best_model_name = name

print("=" * 50)
print(f"🏆 최우수 모델: {best_model_name}\n")

# --- 6. SHAP Value 최종 검증 및 시각화 ---
print(f"{best_model_name} 모델을 기반으로 SHAP 분석을 수행합니다...")

# TreeExplainer를 사용하여 변수별 기여도 계산
explainer = shap.TreeExplainer(models[best_model_name])
shap_values = explainer.shap_values(X_test)

# SHAP Summary Plot 출력
plt.figure(figsize=(10, 6))
shap.summary_plot(shap_values, X_test, show=False)
plt.title(f"SHAP Summary Plot: {best_model_name}", fontsize=15, pad=20)
plt.tight_layout()
plt.show()

print("\n🎉 모든 분석이 완료되었습니다. SHAP 그래프를 통해 각 변수의 연봉 기여도를 확인하세요!")