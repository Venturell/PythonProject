import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from google import genai
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. API 키 및 설정 ---
# ==========================================
# 🚨 여기에 Google AI Studio에서 발급받은 API 키를 입력하세요!
API_KEY = "AIzaSyC키입력하는곳"
MODEL_NAME = 'gemini-2.5-flash'

# ==========================================
# --- 2. 파일 경로 및 변수 설정 ---
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#8\8_PAproject_8_2_grouping.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "8_PAproject_8_2_ANOVA_results.xlsx")

features = [
    'age', 'tenure_years', 'goal_difficulty', 'performance',
    'engagement', 'stress', 'collaboration', 'leadership'
]
NUM_CLUSTERS = 3

print("데이터를 불러오고 K-means 및 ANOVA 분석을 시작합니다...\n")

# ==========================================
# --- 3. 데이터 로드 및 전처리 ---
# ==========================================
df = pd.read_excel(file_path)
df_cluster = df[features].dropna().copy()

# K-means를 위한 데이터 표준화
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df_cluster)

# ==========================================
# --- 4. K-means 군집 분석 수행 ---
# ==========================================
kmeans = KMeans(n_clusters=NUM_CLUSTERS, random_state=42, n_init=10)
df_cluster['Cluster'] = kmeans.fit_predict(X_scaled)

# 군집별 특성 파악 (AI 프롬프트용)
cluster_summary = df_cluster.groupby('Cluster').mean().round(2)
cluster_counts = df_cluster['Cluster'].value_counts().sort_index()

# ==========================================
# --- 5. ANOVA 및 사후검정(Tukey HSD) ---
# ==========================================
# 1) ANOVA (분산분석)
# performance 값이 군집(Cluster)에 따라 차이가 있는지 검정
model = ols('performance ~ C(Cluster)', data=df_cluster).fit()
anova_table = sm.stats.anova_lm(model, typ=2)

p_value = anova_table['PR(>F)']['C(Cluster)']
is_significant = p_value < 0.05

# 2) 사후검정 (Tukey HSD)
# ANOVA에서 유의미한 차이가 있다면, 구체적으로 어느 군집 간에 차이가 있는지 확인
if is_significant:
    tukey = pairwise_tukeyhsd(endog=df_cluster['performance'], groups=df_cluster['Cluster'], alpha=0.05)
    tukey_summary = tukey.summary().as_text()
else:
    tukey_summary = "ANOVA 결과 그룹 간 유의미한 차이가 없어 사후검정을 수행하지 않았습니다."

# ==========================================
# --- 6. Gemini API를 이용한 종합 해석 ---
# ==========================================
print("🤖 Gemini 2.5 Flash 모델이 분석 결과를 종합적으로 해석 중입니다...\n")

analysis_context = f"""
[군집별 변수 평균 (Cluster Centroids) 및 직원 수]
{pd.concat([cluster_counts.rename('Count'), cluster_summary], axis=1).to_string()}

[ANOVA (분산분석) 결과 - 종속변수: performance]
P-value: {p_value:.4f} (0.05 미만일 경우 군집 간 성과 차이가 통계적으로 유의미함)

[Tukey HSD 사후검정 결과]
{tukey_summary}
"""

prompt = f"""
당신은 통계 분석과 조직 관리에 능통한 피플애널리틱스 전문가입니다.
아래는 직원 데이터를 바탕으로 K-means 군집화(K=3)를 수행한 후, 도출된 3개의 그룹 간에 '성과(performance)' 차이가 있는지 ANOVA 및 사후검정을 진행한 결과입니다.

이 데이터를 바탕으로 경영진에게 보고할 요약 보고서를 아래 목차에 맞춰 작성해 주세요:

1. 각 군집(Cluster 0, 1, 2)의 특징 요약 및 페르소나 명명
   - 주어진 '변수 평균' 데이터를 근거로 각 그룹의 특징을 정의하세요.
2. 성과(performance) 차이에 대한 통계적 검증 결과 해석
   - ANOVA p-value와 사후검정(Tukey) 결과를 바탕으로, "어느 그룹의 성과가 가장 높고 낮은지, 그리고 그 차이가 우연인지 아니면 통계적으로 뚜렷한(유의미한) 차이인지"를 실무진이 이해하기 쉽게 설명해 주세요.
3. 성과 향상을 위한 맞춤형 HR Action Plan
   - 도출된 페르소나와 성과 차이를 바탕으로, 상대적으로 성과가 낮은 그룹의 성과를 끌어올리거나, 높은 그룹을 유지하기 위한 보상/교육/조직문화 차원의 HR 전략을 제시해 주세요.

{analysis_context}
"""

try:
    client = genai.Client(api_key=API_KEY)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )
    interpretation = response.text
    print("=" * 70)
    print("💡 [Gemini AI 통합 분석 보고서]")
    print("=" * 70)
    print(interpretation)
    print("=" * 70)

except Exception as e:
    interpretation = f"API 호출 중 오류가 발생했습니다: {e}"
    print(interpretation)

# ==========================================
# --- 7. 엑셀 파일로 결과 저장 ---
# ==========================================
# 원본 데이터에 Cluster 병합
df_final = df.copy()
df_final['Cluster'] = np.nan
df_final.loc[df_cluster.index, 'Cluster'] = df_cluster['Cluster']

# 엑셀 저장을 위한 사후검정 결과 데이터프레임 변환 (결과가 있을 경우)
if is_significant:
    tukey_df = pd.DataFrame(data=tukey._results_table.data[1:], columns=tukey._results_table.data[0])
else:
    tukey_df = pd.DataFrame({'Message': ["사후검정 결과 없음 (ANOVA 비유의)"]})

with pd.ExcelWriter(output_path) as writer:
    # 1. 클러스터 라벨이 추가된 전체 데이터
    df_final.to_excel(writer, sheet_name='Data_with_Clusters', index=False)

    # 2. 클러스터별 특성 평균 및 인원수
    pd.concat([cluster_counts.rename('Count'), cluster_summary], axis=1).to_excel(writer, sheet_name='Cluster_Summary')

    # 3. ANOVA 검정 결과표
    anova_table.to_excel(writer, sheet_name='ANOVA_Result')

    # 4. Tukey HSD 사후검정 결과표
    tukey_df.to_excel(writer, sheet_name='Tukey_Posthoc', index=False)

    # 5. AI 해석 결과 (텍스트)
    pd.DataFrame({'AI Interpretation': [interpretation]}).to_excel(writer, sheet_name='AI_Insights', index=False)

print(f"\n✅ 분석 및 통계 검증이 완료되었습니다. 결과가 엑셀 파일로 저장되었습니다.\n저장 경로: {output_path}")