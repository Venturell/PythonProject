import pandas as pd
import os
from sklearn.ensemble import RandomForestClassifier

# 1. 파일 경로 설정
base_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#1"
train_path = os.path.join(base_path, "1_PAproject_1_4_Applewatch.csv")
predict_path = os.path.join(base_path, "1_PAproject_1_4_Applewatch_prediction.csv")
output_path = os.path.join(base_path, "1_PAproject_1_4_Applewatch_Prediction_Result.xlsx")

# 2. 데이터 불러오기
print("데이터를 불러오는 중입니다...")
train_df = pd.read_csv(train_path)
predict_df = pd.read_csv(predict_path)

# 3. 독립변수(X)와 종속변수(y) 설정
features = [
    "age", "gender", "height", "weight",
    "Applewatch.Steps_LE", "Applewatch.Heart_LE", "Applewatch.Calories_LE",
    "Applewatch.Distance_LE", "EntropyApplewatchHeartPerDay_LE",
    "EntropyApplewatchStepsPerDay_LE", "RestingApplewatchHeartrate_LE",
    "CorrelationApplewatchHeartrateSteps_LE", "NormalizedApplewatchHeartrate_LE",
    "ApplewatchIntensity_LE", "SDNormalizedApplewatchHR_LE", "ApplewatchStepsXDistance_LE"
]
target = "activity_trimmed"

# 학습용 데이터 결측치 제거
train_df = train_df.dropna(subset=features + [target])
X_train = train_df[features]
y_train = train_df[target]

# 예측용 데이터 결측치 0으로 채우기
predict_df[features] = predict_df[features].fillna(0)
X_predict = predict_df[features]

# 4. 랜덤 포레스트 모델 학습
print("모델 학습을 시작합니다...")
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

# 5. 예측 수행
print("예측을 수행하는 중입니다...")
predictions = rf_model.predict(X_predict)
predict_df["Predicted_activity_trimmed"] = predictions

# 6. 엑셀(Excel) 파일로 결과 저장
predict_df.to_excel(output_path, index=False)
print(f"성공! 예측 결과가 저장되었습니다: {output_path}\n")

# 7. 변수 중요도 분석 출력 (교수님 화면과 동일하게 출력되도록 추가된 부분!)
print("[변수 중요도 분석]")
importances = pd.Series(rf_model.feature_importances_, index=features)
# 수치가 높은 순서대로(내림차순) 정렬하여 출력
print(importances.sort_values(ascending=False))