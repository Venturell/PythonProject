import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import platform
import warnings
from sklearn.ensemble import RandomForestRegressor

warnings.filterwarnings('ignore')

# --- 1. 한글 폰트 설정 (시각화 시 깨짐 방지) ---
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# --- 2. 파일 경로 설정 ---
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#6\6_PAproject_6_3_AI.csv"
output_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#6\AI_Education_Targeting_List.csv"

print("데이터를 불러오고 전처리를 시작합니다...")
df = pd.read_csv(file_path)

# --- 3. 데이터 전처리 (Wide format 변환) ---
# DiD 패널 데이터를 사원(emp_id) 1명당 1줄의 데이터로 재구조화합니다.
df_post0 = df[df['post'] == 0].set_index('emp_id')
df_post1 = df[df['post'] == 1].set_index('emp_id')

df_wide = df_post0[['treatment', 'dept', 'grade_num', 'tenure', 'age']].copy()
df_wide['perf_pre'] = df_post0['perf_score']   # 사전 점수
df_wide['perf_post'] = df_post1['perf_score']  # 사후 점수

# 종속변수: 성과 변화량 (delta_score)
df_wide['delta_score'] = df_wide['perf_post'] - df_wide['perf_pre']
df_wide = df_wide.dropna(subset=['delta_score', 'tenure', 'age', 'grade_num', 'perf_pre'])

# 범주형 변수(부서) 더미화 (One-Hot Encoding)
df_wide = pd.get_dummies(df_wide, columns=['dept'], drop_first=True)

# 모델링에 사용할 특성(Features) 정의
features = [col for col in df_wide.columns if col not in ['treatment', 'perf_pre', 'perf_post', 'delta_score']]
# 사전 성과(perf_pre)도 통제 변수로 포함
features.append('perf_pre')

X = df_wide[features]
y = df_wide['delta_score']
t = df_wide['treatment']

# --- 4. T-Learner 모델 학습 (Causal ML) ---
print("\nT-Learner 기반 머신러닝 모델(Random Forest) 학습 중...")

# 1) Control 모델 (교육 미참석자의 성과 변화를 학습)
rf0 = RandomForestRegressor(n_estimators=100, random_state=42)
rf0.fit(X[t == 0], y[t == 0])

# 2) Treatment 모델 (교육 참석자의 성과 변화를 학습)
rf1 = RandomForestRegressor(n_estimators=100, random_state=42)
rf1.fit(X[t == 1], y[t == 1])

# --- 5. 개별 처치 효과 (ITE: Individual Treatment Effect) 추정 ---
# 모든 직원이 '교육을 받았을 때의 예상 점수 상승폭' - '안 받았을 때의 예상 점수 상승폭'
df_wide['pred_delta_1'] = rf1.predict(X)
df_wide['pred_delta_0'] = rf0.predict(X)
df_wide['ITE'] = df_wide['pred_delta_1'] - df_wide['pred_delta_0']

# --- 6. 교육 효과를 결정짓는 변수 중요도 (Meta-Learner 적용) ---
# 산출된 ITE(교육 효과) 자체를 종속변수로 두고 예측하는 설명용 모델 생성
explainer_rf = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
explainer_rf.fit(X, df_wide['ITE'])

importances = explainer_rf.feature_importances_
fi_df = pd.DataFrame({'Feature': X.columns, 'Importance': importances}).sort_values(by='Importance', ascending=False)

# 변수 중요도 시각화
plt.figure(figsize=(10, 6))
sns.barplot(x='Importance', y='Feature', data=fi_df, palette='viridis')
plt.title('🎯 어떤 요인이 AI 교육 효과(ITE) 크기를 결정하는가?', fontsize=15)
plt.xlabel('중요도 (Feature Importance)')
plt.ylabel('직원 특성')
plt.tight_layout()
plt.show()

# --- 7. 고효과 그룹 (Top 10%) 프로파일링 ---
threshold = df_wide['ITE'].quantile(0.9)
top_10_group = df_wide[df_wide['ITE'] >= threshold]

print("\n" + "="*50)
print("🌟 [분석 결과] AI 교육 '고효과(Top 10%)' 타겟 그룹 프로필")
print("="*50)
print(f"전체 직원의 평균 예상 교육 효과(ITE): +{df_wide['ITE'].mean():.2f}점")
print(f"Top 10% 직원의 평균 예상 교육 효과(ITE): +{top_10_group['ITE'].mean():.2f}점\n")

print("📊 Top 10% 그룹 vs 전체 그룹 평균 비교:")
compare_df = pd.DataFrame({
    '전체 평균': df_wide[['tenure', 'age', 'grade_num', 'perf_pre']].mean(),
    'Top 10% 평균': top_10_group[['tenure', 'age', 'grade_num', 'perf_pre']].mean()
})
print(compare_df.round(2))
print("="*50)

# --- 8. 결과 엑셀/CSV 저장 ---
# ITE가 높은 순으로 정렬하여 저장
result_df = df_wide.sort_values(by='ITE', ascending=False).reset_index()
result_df.to_csv(output_path, index=False, encoding='utf-8-sig') # 한글 깨짐 방지
print(f"\n✅ 타겟팅 명단(ITE 점수 포함) 저장 완료!\n경로: {output_path}")