import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.preprocessing import LabelEncoder
import statsmodels.api as sm

# 1. 파일 경로 설정 및 데이터 로드
# 사용자님의 경로를 변수에 저장합니다. (파일이 해당 경로에 있어야 합니다.)
file_path = r'C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#5\5_PAproject_5_4_rater.xlsx'
df = pd.read_excel(file_path)

# 2. 고성과자 정의 (상위 20% 기준)
# performance_true를 기준으로 내림차순 정렬 후 상위 20%를 1, 나머지를 0으로 분류
threshold = df['performance_true'].quantile(0.8)
df['high_performer'] = (df['performance_true'] >= threshold).astype(int)

# 3. 데이터 전처리
# 분석에 사용할 변수 선택
features = ['department', 'job_level', 'age', 'tenure_years', 'goal_difficulty']
X = df[features].copy()
y = df['high_performer']

# 범주형 변수 처리 (One-Hot Encoding)
# 로지스틱 회귀와 랜덤포레스트 분석을 위해 텍스트 데이터를 숫자로 변환합니다.
X_encoded = pd.get_dummies(X, columns=['department', 'job_level'], drop_first=True)

# 4. 모델 학습 및 평가 (Train/Test Split)
X_train, X_test, y_train, y_test = train_test_split(X_encoded, y, test_size=0.2, random_state=42, stratify=y)

# [모델 1] 로지스틱 회귀 (Odds Ratio 산출용)
log_reg = LogisticRegression(max_iter=1000)
log_reg.fit(X_train, y_train)

# [모델 2] 랜덤 포레스트 (변수 중요도 산출용)
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

# 5. 성능 평가 (Accuracy & AUC)
# 로지스틱 회귀 성능
log_acc = accuracy_score(y_test, log_reg.predict(X_test))
log_auc = roc_auc_score(y_test, log_reg.predict_proba(X_test)[:, 1])

# 랜덤 포레스트 성능
rf_acc = accuracy_score(y_test, rf_model.predict(X_test))
rf_auc = roc_auc_score(y_test, rf_model.predict_proba(X_test)[:, 1])

model_perf = pd.DataFrame({
    'Model': ['Logistic Regression', 'Random Forest'],
    'Accuracy': [log_acc, rf_acc],
    'AUC': [log_auc, rf_auc]
})

# 6. 영향력 분석 (Odds Ratio & Feature Importance)
# 로지스틱 회귀 Odds Ratio (계수의 지수함수 값)
odds_ratios = pd.DataFrame({
    'Feature': X_encoded.columns,
    'Odds_Ratio': np.exp(log_reg.coef_[0])
}).sort_values(by='Odds_Ratio', ascending=False)

# 랜덤 포레스트 변수 중요도
feature_importances = pd.DataFrame({
    'Feature': X_encoded.columns,
    'Importance': rf_model.feature_importances_
}).sort_values(by='Importance', ascending=False)

# 7. 전체 직원 예측 확률 부여
df['pred_prob'] = rf_model.predict_proba(X_encoded)[:, 1]

# 8. 고성과자 vs 일반직원 프로필 비교 (평균 차이)
profile_summary = df.groupby('high_performer')[['age', 'tenure_years', 'goal_difficulty']].mean().reset_index()
profile_summary['high_performer'] = profile_summary['high_performer'].map({1: '고성과자(Top 20%)', 0: '일반직원'})

# 9. 결과 저장 (Excel)
output_path = r'C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#5\Analysis_Result_HighPerformer.xlsx'
with pd.ExcelWriter(output_path) as writer:
    model_perf.to_excel(writer, sheet_name='1_Model_Performance', index=False)
    odds_ratios.to_excel(writer, sheet_name='2_Odds_Ratio_LogReg', index=False)
    feature_importances.to_excel(writer, sheet_name='3_Feature_Importance_RF', index=False)
    profile_summary.to_excel(writer, sheet_name='4_Group_Profile_Summary', index=False)
    df.to_excel(writer, sheet_name='5_Full_Predictions', index=False)

print(f"분석이 완료되었습니다. 결과 파일이 다음 경로에 저장되었습니다: {output_path}")