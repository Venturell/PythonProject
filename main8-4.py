import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from google import genai
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. API 키 및 설정 ---
# ==========================================
# 🚨 여기에 Google AI Studio에서 발급받은 API 키를 입력하세요!
API_KEY = "AIz키입력하는곳"
MODEL_NAME = 'gemini-2.5-flash'

# ==========================================
# --- 2. 파일 경로 및 변수 설정 ---
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#8\8_PAproject_8_2_grouping.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "8_PAproject_8_2_Kmeans_results.xlsx")

features = [
    'age', 'tenure_years', 'goal_difficulty', 'performance',
    'engagement', 'stress', 'collaboration', 'leadership'
]

# K-means의 K값 설정
NUM_CLUSTERS = 3

print("데이터를 불러오고 K-means 군집 분석(K=3)을 시작합니다...\n")

# ==========================================
# --- 3. 데이터 로드 및 전처리 ---
# ==========================================
df = pd.read_excel(file_path)

# 분석할 변수만 추출하고 결측치가 있는 행 제거
df_cluster = df[features].dropna()

# 군집 분석은 거리 기반이므로 표준화(Standardization) 필수
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df_cluster)

# ==========================================
# --- 4. K-means 군집 분석 수행 ---
# ==========================================
# K-means 모델 생성 및 학습 (재현성을 위해 random_state=42 고정)
kmeans = KMeans(n_clusters=NUM_CLUSTERS, random_state=42, n_init=10)
cluster_labels = kmeans.fit_predict(X_scaled)

# 분석 데이터프레임에 클러스터 라벨 추가
df_cluster['Cluster'] = cluster_labels

# 각 클러스터별 데이터 수 및 특성 평균 파악
cluster_counts = df_cluster['Cluster'].value_counts().sort_index()
cluster_summary = df_cluster.groupby('Cluster').mean().round(2)

# ==========================================
# --- 5. Gemini API를 이용한 결과 해석 ---
# ==========================================
print("🤖 Gemini 2.5 Flash 모델이 K-means 군집 특성을 해석 중입니다...\n")

summary_text = f"""
[군집별 직원 수]
{cluster_counts.to_string()}

[군집별 변수 평균값 (Cluster Centroids)]
{cluster_summary.to_string()}

* 참고: 각 변수의 평균값은 표준화되기 전의 실제 원본 데이터 기준입니다.
"""

prompt = f"""
당신은 기업의 인사 데이터를 다루는 피플애널리틱스 전문가입니다.
아래는 직원들의 데이터(연령, 근속연수, 목표 난이도, 성과, 몰입도, 스트레스, 협업, 리더십)를 바탕으로 K-means Clustering을 수행하여 {NUM_CLUSTERS}개의 그룹으로 나눈 결과입니다.

분석 결과를 바탕으로 다음 세 가지를 수행해 주세요:
1. Cluster 0, 1, 2가 각각 어떤 특징을 가진 직원 그룹인지 인사적 관점에서 명명(Naming)해 주세요. (예: Cluster 0 = '핵심 리더십 발휘 그룹')
2. 각 군집을 그렇게 명명한 이유를 제시된 '군집별 변수 평균값' 데이터를 근거로 구체적으로 설명해 주세요. 특히 타 군집 대비 유의미하게 높거나 낮은 수치를 중심으로 설명하세요.
3. 이 3가지 유형의 직원 그룹별로 HR 부서가 어떤 맞춤형 인사 제도(보상, 교육, 멘토링, 복지 등)를 도입해야 할지 구체적인 Action Plan을 제시해 주세요.

{summary_text}
"""

try:
    client = genai.Client(api_key=API_KEY)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )
    interpretation = response.text
    print("=" * 60)
    print("💡 [Gemini AI 분석 결과]")
    print("=" * 60)
    print(interpretation)
    print("=" * 60)

except Exception as e:
    interpretation = f"API 호출 중 오류가 발생했습니다: {e}"
    print(interpretation)

# ==========================================
# --- 6. 엑셀 파일로 결과 저장 ---
# ==========================================
# 원본 데이터에 Cluster 라벨 추가 (결측치가 제거된 인덱스 기준)
df_final = df.copy()
df_final['KMeans_Cluster'] = np.nan
df_final.loc[df_cluster.index, 'KMeans_Cluster'] = cluster_labels

# 클러스터 크기 요약을 데이터프레임으로 변환
df_counts = pd.DataFrame({'Cluster': cluster_counts.index, 'Employee_Count': cluster_counts.values})

with pd.ExcelWriter(output_path) as writer:
    # 1. K-means 군집 결과가 포함된 전체 데이터
    df_final.to_excel(writer, sheet_name='Clustered_Data', index=False)

    # 2. 클러스터별 특성 요약 (평균값)
    cluster_summary.to_excel(writer, sheet_name='Cluster_Summary')

    # 3. 클러스터별 직원 수
    df_counts.to_excel(writer, sheet_name='Cluster_Counts', index=False)

    # 4. AI 해석 결과 (텍스트로 저장)
    pd.DataFrame({'AI Interpretation': [interpretation]}).to_excel(writer, sheet_name='AI_Insights', index=False)

print(f"\n✅ K-means 분석이 완료되었습니다. 결과가 엑셀 파일로 저장되었습니다.\n저장 경로: {output_path}")