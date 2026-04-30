import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
import matplotlib.pyplot as plt
import os
import warnings
from google import genai

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. API 키 및 설정 ---
# ==========================================
# 🚨 여기에 Google AI Studio에서 발급받은 API 키를 입력하세요!
API_KEY = "AIzgemini키입력"
MODEL_NAME = 'gemini-2.5-flash'

# ==========================================
# --- 2. 파일 경로 및 변수 설정 ---
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#8\8_PAproject_8_2_grouping.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "8_PAproject_8_2_Dendrogram_results.xlsx")

features = [
    'age', 'tenure_years', 'goal_difficulty', 'performance',
    'engagement', 'stress', 'collaboration', 'leadership'
]

print("데이터를 불러오고 계층적 군집화 분석을 시작합니다...\n")

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
# --- 4. 계층적 군집화 및 Dendrogram 생성 ---
# ==========================================
# Ward 방법(오차제곱합 최소화)과 유클리디안 거리 사용
Z = linkage(X_scaled, method='ward', metric='euclidean')

# Dendrogram 시각화
plt.figure(figsize=(15, 8))
plt.title('Hierarchical Clustering Dendrogram (Ward)', fontsize=16)
plt.xlabel('Employee Index', fontsize=12)
plt.ylabel('Distance (Ward)', fontsize=12)

# 너무 많은 데이터가 있으면 아래쪽이 복잡해지므로 트렁케이션(Truncation) 적용
dendrogram(
    Z,
    truncate_mode='lastp',  # 마지막 p개의 병합만 표시
    p=30,  # 표시할 노드 수
    leaf_rotation=90.,
    leaf_font_size=10.,
    show_contracted=True
)

# 그래프 화면에 표시 (저장 원할 시 plt.savefig() 추가)
plt.show()

# ==========================================
# --- 5. 클러스터 할당 (임의로 3개 군집 설정) ---
# ==========================================
# 덴드로그램을 보고 적절한 군집 수를 정해야 하지만, 해석을 위해 자동 3개 할당
num_clusters = 3
cluster_labels = fcluster(Z, num_clusters, criterion='maxclust')
df_cluster['Cluster'] = cluster_labels

# 각 클러스터별 평균 특성 파악 (AI 해석용)
cluster_summary = df_cluster.groupby('Cluster').mean().round(2)

# ==========================================
# --- 6. Gemini API를 이용한 결과 해석 ---
# ==========================================
print("🤖 Gemini 2.5 Flash 모델이 군집 특성을 해석 중입니다...\n")

summary_text = f"""
[군집별 변수 평균값 (Cluster Centroids)]
{cluster_summary.to_string()}

* 참고: 각 변수는 표준화되기 전의 실제 원본 데이터 기준 평균입니다.
"""

prompt = f"""
당신은 기업의 인사 데이터를 다루는 피플애널리틱스 전문가입니다.
아래는 직원들의 데이터(연령, 근속연수, 목표 난이도, 성과, 몰입도, 스트레스, 협업, 리더십)를 바탕으로 계층적 군집화(Hierarchical Clustering)를 수행하여 {num_clusters}개의 그룹으로 나눈 결과입니다.

분석 결과를 바탕으로 다음 세 가지를 수행해 주세요:
1. Cluster 1, 2, 3이 각각 어떤 특징을 가진 직원 그룹인지 인사적 관점에서 명명(Naming)해 주세요. (예: Cluster 1 = '고성과-고스트레스 워커홀릭 그룹')
2. 각 군집을 그렇게 명명한 이유를 제시된 '군집별 변수 평균값' 데이터를 근거로 구체적으로 설명해 주세요.
3. 이 3가지 유형의 직원 그룹별로 HR 부서가 어떤 맞춤형 지원이나 관리 전략을 펼쳐야 할지 각각의 Action Plan을 간략히 제시해 주세요.

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
# --- 7. 엑셀 파일로 결과 저장 ---
# ==========================================
# 원본 데이터에 Cluster 라벨 추가 (결측치가 제거된 인덱스 기준)
df_final = df.copy()
df_final['Cluster'] = np.nan
df_final.loc[df_cluster.index, 'Cluster'] = cluster_labels

with pd.ExcelWriter(output_path) as writer:
    # 1. 클러스터 할당 결과가 포함된 전체 데이터
    df_final.to_excel(writer, sheet_name='Clustered_Data', index=False)

    # 2. 클러스터별 특성 요약 (평균값)
    cluster_summary.to_excel(writer, sheet_name='Cluster_Summary')

    # 3. AI 해석 결과 (텍스트로 저장)
    pd.DataFrame({'AI Interpretation': [interpretation]}).to_excel(writer, sheet_name='AI_Insights', index=False)

print(f"\n✅ 분석이 완료되었습니다. 결과가 엑셀 파일로 저장되었습니다.\n저장 경로: {output_path}")