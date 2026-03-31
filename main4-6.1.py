import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import platform
import warnings

warnings.filterwarnings('ignore')  # 불필요한 경고 메시지 숨김

# 머신러닝 및 평가 지표 라이브러리
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

# XAI 라이브러리 (설명 가능한 AI)
import shap

# --- 한글 폰트 및 마이너스 기호 깨짐 방지 설정 ---
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# 1. 파일 경로 설정 및 데이터 불러오기 (cp949 인코딩)
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3\3_PAproject_3_3_NPS.csv"

print("데이터를 불러오고 전처리를 시작합니다...")
df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

# 2. 필터링: 정상 가입(1) & 가입자수 200명 이상
df_filtered = df[(df['사업장가입상태코드'] == 1) & (df['가입자수'] >= 200)].copy()

# 3. 연봉 추정 계산 (원 단위 그대로 유지)
df_filtered['당월고지금액'] = pd.to_numeric(df_filtered['당월고지금액'], errors='coerce')
df_filtered['가입자수'] = pd.to_numeric(df_filtered['가입자수'], errors='coerce')
df_filtered['인당금액'] = df_filtered['당월고지금액'] / df_filtered['가입자수']
df_filtered['연봉'] = (df_filtered['인당금액'] / 0.095) * 12

# 4. 적용일자에서 연도 추출
df_filtered['적용일자'] = pd.to_datetime(df_filtered['적용일자'], format='%Y-%m-%d', errors='coerce')
df_filtered['연도'] = df_filtered['적용일자'].dt.year

# 5. 분석 대상 산업 및 지역 필터링
target_industry = [722000, 551001, 671202, 724000]
target_region = [41, 11, 28, 52]

df_filtered['사업장업종코드'] = pd.to_numeric(df_filtered['사업장업종코드'], errors='coerce')
df_filtered['법정동주소광역시도코드'] = pd.to_numeric(df_filtered['법정동주소광역시도코드'], errors='coerce')

df_final = df_filtered[(df_filtered['사업장업종코드'].isin(target_industry)) &
                       (df_filtered['법정동주소광역시도코드'].isin(target_region))].copy()

# 필요한 변수만 남기고 결측치 제거
vars_to_keep = ['연봉', '가입자수', '연도', '사업장업종코드', '법정동주소광역시도코드']
df_final = df_final[vars_to_keep].dropna()

print(f"총 {len(df_final)}개의 기업 데이터로 머신러닝 학습을 시작합니다.\n")

# --- 6. 더미 코딩 (One-Hot Encoding) ---
df_final['사업장업종코드'] = df_final['사업장업종코드'].astype(int).astype(str)
df_final['법정동주소광역시도코드'] = df_final['법정동주소광역시도코드'].astype(int).astype(str)

# 다중공선성을 통제하기 위해 drop_first=True로 설정 (기준점 1개씩 숨김)
df_dummy = pd.get_dummies(df_final, columns=['사업장업종코드', '법정동주소광역시도코드'], drop_first=True, dtype=int)

# 독립변수(X)와 종속변수(y) 분리
X = df_dummy.drop('연봉', axis=1)
y = df_dummy['연봉']

# 학습 데이터(Train)와 테스트 데이터(Test)를 8:2로 분할
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# --- 7. 모델 학습 및 성능 평가 (RF, XGB, LGBM) ---
models = {
    'Random Forest': RandomForestRegressor(random_state=42),
    'XGBoost': XGBRegressor(random_state=42),
    'LightGBM': LGBMRegressor(
        random_state=42,
        min_child_samples=5,  # 핵심 수정: 데이터가 적은 범주형(더미) 변수도 무시하지 않도록 조건 완화
        max_depth=5,
        learning_rate=0.05,
        n_estimators=200,
        verbose=-1
    )
}

results = {}
feature_importances = {}

print("=" * 60)
print(f"{'Model':<15} | {'R-squared (R2)':<15} | {'RMSE (만원)':<15}")
print("-" * 60)

for name, model in models.items():
    # 학습
    model.fit(X_train, y_train)
    # 예측
    pred = model.predict(X_test)

    # 평가 지표 계산 (RMSE는 가독성을 위해 만원 단위로 표기)
    r2 = r2_score(y_test, pred)
    rmse = np.sqrt(mean_squared_error(y_test, pred)) / 10000

    results[name] = {'R2': r2, 'RMSE': rmse}
    feature_importances[name] = model.feature_importances_

    print(f"{name:<15} | {r2:<15.4f} | {rmse:<15.0f}")
print("=" * 60)

# 가장 성능이 좋은(R2가 높은) 모델 선택
best_model_name = max(results, key=lambda k: results[k]['R2'])
best_model = models[best_model_name]
print(f"\n🏆 가장 예측 성능이 좋은 모델: {best_model_name}")

# --- 특성 중요도(Feature Importance) 일관성 비교 시각화 ---
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('모델별 변수 중요도 (Feature Importance) 비교', fontsize=16, fontweight='bold', y=1.05)

for i, (name, imp) in enumerate(feature_importances.items()):
    # 중요도를 보기 좋게 정렬
    sorted_idx = np.argsort(imp)
    axes[i].barh(X.columns[sorted_idx], imp[sorted_idx], color='teal')
    axes[i].set_title(f'{name} Feature Importance')
    axes[i].set_xlabel('Importance Score')

plt.tight_layout()
plt.show()

# --- 8. SHAP Value 기반 최종 해석 (Best Model 사용) ---
print(f"\n최고 성능 모델({best_model_name})을 바탕으로 SHAP Value 검증을 시작합니다...")

# Tree 기반 모델 전용 SHAP Explainer 사용
explainer = shap.TreeExplainer(best_model)
shap_values = explainer.shap_values(X_test)

# SHAP Summary Plot 시각화
plt.figure(figsize=(10, 6))
plt.title(f'SHAP Value Summary Plot ({best_model_name})', fontsize=14, fontweight='bold', pad=20)
shap.summary_plot(shap_values, X_test, plot_type="dot", show=False)
plt.tight_layout()
plt.show()

print("\n🎉 머신러닝 모델 학습 및 SHAP 분석이 완벽하게 종료되었습니다!")