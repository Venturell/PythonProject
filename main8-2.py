import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from google import genai
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. API 키 및 설정 ---
# ==========================================
# 🚨 여기에 Google AI Studio에서 발급받은 API 키를 입력하세요!
API_KEY = "AI제미나이api키입력하Q"
MODEL_NAME = 'gemini-2.5-flash'

# ==========================================
# --- 2. 파일 경로 및 변수 설정 ---
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#8\8_PAproject_8_2_grouping.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "8_PAproject_8_2_PCA_results.xlsx")

features = [
    'age', 'tenure_years', 'goal_difficulty', 'performance',
    'engagement', 'stress', 'collaboration', 'leadership'
]

print("데이터를 불러오고 PCA 분석을 시작합니다...\n")

# ==========================================
# --- 3. 데이터 로드 및 전처리 ---
# ==========================================
df = pd.read_excel(file_path)

# 분석할 변수만 추출하고 결측치가 있는 행 제거
df_pca = df[features].dropna()

# PCA는 데이터의 스케일에 민감하므로 표준화(Standardization) 수행
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df_pca)

# ==========================================
# --- 4. 주성분 분석(PCA) 수행 ---
# ==========================================
# 전체 변수 개수만큼 주성분 생성
pca = PCA()
pca_scores = pca.fit_transform(X_scaled)

# 설명된 분산 비율 (각 주성분이 데이터를 얼마나 설명하는지)
explained_variance = pca.explained_variance_ratio_

# 요인 적재량 (각 변수가 주성분에 미치는 영향력)
loadings = pd.DataFrame(
    pca.components_.T,
    columns=[f'PC{i + 1}' for i in range(len(features))],
    index=features
)

# PCA 점수를 데이터프레임으로 변환 (해석의 편의를 위해 상위 3개 주성분만 주로 활용)
df_scores = pd.DataFrame(
    pca_scores[:, :3],
    columns=['PC1', 'PC2', 'PC3'],
    index=df_pca.index
)
df_final = pd.concat([df.loc[df_pca.index], df_scores], axis=1)

# ==========================================
# --- 5. Gemini API를 이용한 결과 해석 ---
# ==========================================
print("🤖 Gemini 2.5 Flash 모델이 PCA 결과를 해석 중입니다...\n")

# AI에게 전달할 분석 결과 텍스트 포맷팅
pca_summary = f"""
[주성분 분산 설명력]
PC1: {explained_variance[0] * 100:.2f}%
PC2: {explained_variance[1] * 100:.2f}%
PC3: {explained_variance[2] * 100:.2f}%

[상위 3개 주성분의 요인 적재량(Loadings)]
{loadings[['PC1', 'PC2', 'PC3']].round(3).to_string()}
"""

prompt = f"""
당신은 기업의 인사 데이터를 다루는 피플애널리틱스 전문가입니다.
아래는 직원들의 데이터(연령, 근속연수, 목표 난이도, 성과, 몰입도, 스트레스, 협업, 리더십)를 바탕으로 주성분 분석(PCA)을 수행한 결과입니다.

분석 결과를 바탕으로 다음 세 가지를 수행해 주세요:
1. PC1, PC2, PC3가 각각 어떤 인사적 의미를 갖는 변수들의 묶음인지 명명(Naming)해 주세요. (예: PC1 = '근속 및 성과 역량 요인')
2. 각 주성분을 그렇게 명명한 이유를 요인 적재량(Loadings)의 양수/음수 값과 크기를 근거로 논리적으로 설명해 주세요.
3. 이 분석 결과를 실제 HR 실무(예: 인재 그룹핑, 조직 진단)에 어떻게 활용할 수 있을지 간략한 인사이트를 제시해 주세요.

{pca_summary}
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
# 여러 시트로 나누어 저장
with pd.ExcelWriter(output_path) as writer:
    # 1. 원본 데이터 + 상위 3개 주성분 점수
    df_final.to_excel(writer, sheet_name='PCA_Scores', index=False)

    # 2. 요인 적재량 (Loadings)
    loadings.to_excel(writer, sheet_name='Loadings')

    # 3. 분산 설명력
    pd.DataFrame({
        'Principal Component': [f'PC{i + 1}' for i in range(len(features))],
        'Explained Variance Ratio': explained_variance,
        'Cumulative Variance Ratio': np.cumsum(explained_variance)
    }).to_excel(writer, sheet_name='Explained_Variance', index=False)

    # 4. AI 해석 결과 (텍스트로 저장)
    pd.DataFrame({'AI Interpretation': [interpretation]}).to_excel(writer, sheet_name='AI_Insights', index=False)

print(f"\n✅ 분석이 완료되었습니다. 결과가 엑셀 파일로 저장되었습니다.\n저장 경로: {output_path}")