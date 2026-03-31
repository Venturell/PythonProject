import pandas as pd
import numpy as np
import platform
import warnings
import matplotlib.pyplot as plt  # 💡 바로 이 줄이 추가되었습니다!

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score

warnings.filterwarnings('ignore') # 불필요한 경고 메시지 숨김

# --- 1. 한글 폰트 설정 ---
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# --- 2. 데이터 불러오기 ---
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#2\2_PAproject_2_4_machine.csv"
print("데이터를 불러오고 전처리를 시작합니다...")

# (Dtype 경고 방지를 위해 low_memory=False 추가)
df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

# --- 3. 분석 변수 설정 ---
features = ['Department', 'Performance_Rating', 'Salary', 'Work_Hours']
target = 'Left'

X = df[features]
y = df[target]

# --- 4. 범주형 변수 처리 (One-Hot Encoding) ---
# Department(Sales, Mkt, HR, Eng, R&D)를 머신러닝이 이해할 수 있도록 더미 변수로 변환
X_encoded = pd.get_dummies(X, columns=['Department'], drop_first=False)

# --- 5. 학습용 / 테스트용 데이터 분할 (8:2) ---
X_train, X_test, y_train, y_test = train_test_split(X_encoded, y, test_size=0.2, random_state=42)

# --- 6. 데이터 스케일링 (SVM의 핵심) ---
# SVM은 거리 기반 알고리즘이므로, 단위가 다른 연봉과 근무시간 등을 동일한 스케일로 맞춤
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# --- 7. SVM 모델 학습 ---
print("SVM 모델을 학습하고 있습니다...")
svm_model = SVC(kernel='rbf', probability=True, random_state=42)
svm_model.fit(X_train_scaled, y_train)

# 모델 성능 확인
y_pred = svm_model.predict(X_test_scaled)
accuracy = accuracy_score(y_test, y_pred)
print(f"✅ 모델 학습 완료! (테스트 데이터 예측 정확도: {accuracy * 100:.1f}%)\n")

# =====================================================================
# --- 8. 가상의 직원(Target Employee) 퇴사 예측 ---
# =====================================================================
print("-" * 50)
print("🔍 [가상 직원 퇴사 예측 테스트]")
print("조건: 영업부(Sales), 성과 2등급, 연봉 2000, 주 60시간 근무")
print("-" * 50)

# 가상 직원의 데이터를 데이터프레임으로 생성
new_employee = pd.DataFrame({
    'Department': ['Sales'],
    'Performance_Rating': [2],
    'Salary': [2000],
    'Work_Hours': [60]
})

# 기존 데이터와 동일하게 더미 코딩 적용
new_encoded = pd.get_dummies(new_employee, columns=['Department'])

# 🚨 중요: 학습 데이터에 있던 모든 부서 컬럼 구조를 동일하게 맞춰줌 (없는 부서는 0)
new_encoded = new_encoded.reindex(columns=X_encoded.columns, fill_value=0)

# 가상 직원 데이터 스케일링
new_scaled = scaler.transform(new_encoded)

# SVM으로 퇴사 여부 및 확률 예측
prediction = svm_model.predict(new_scaled)
probabilities = svm_model.predict_proba(new_scaled)[0] # [잔류 확률, 퇴사 확률]

if prediction[0] == 1:
    result_text = "🚨 이직(퇴사)할 것으로 예측됩니다."
else:
    result_text = "🟢 회사에 잔류할 것으로 예측됩니다."

print(f"▶ 예측 결과: {result_text}")
print(f"▶ 상세 확률: 퇴사 확률 {probabilities[1]*100:.1f}% / 잔류 확률 {probabilities[0]*100:.1f}%")
print("-" * 50)