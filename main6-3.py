import pandas as pd
import statsmodels.formula.api as smf
from google import genai
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. Gemini API 설정 ---
# ==========================================
# 🚨 여기에 Google AI Studio에서 발급받은 API 키를 입력하세요!
API_KEY = "AIzaSyCHr어쩌구api키입력"
client = genai.Client(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash'

# ==========================================
# --- 2. 데이터 불러오기 및 전처리 ---
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#6\6_PAproject_6_3_AI.csv"

print("데이터를 불러오고 전처리를 시작합니다...")
df = pd.read_csv(file_path)

# 사전 성과(pre_score) 변수 생성:
# post가 0일 때의 perf_score를 emp_id 기준으로 가져와 새로운 컬럼으로 매핑합니다.
pre_scores = df[df['post'] == 0][['emp_id', 'perf_score']].rename(columns={'perf_score': 'pre_score'})
df = df.merge(pre_scores, on='emp_id', how='left')

# 분석을 위해 결측치가 있는 행 제거
df = df.dropna(subset=['perf_score', 'treatment', 'post', 'grade_num', 'tenure', 'pre_score'])

# ==========================================
# --- 3. 이중차분법(DiD) 모형 분석 ---
# ==========================================
# DiD의 핵심은 treatment와 post의 교호작용항(treatment:post)의 계수입니다.

# [모형 1] 기본 DiD: 처치여부(treatment) * 시점(post)
m1 = smf.ols("perf_score ~ treatment * post", data=df).fit()

# [모형 2] 시간 불변 특성(인적자본 등) 통제: 기본 DiD + 직급(grade_num) + 근속(tenure)
m2 = smf.ols("perf_score ~ treatment * post + grade_num + tenure", data=df).fit()

# [모형 3] 인적자본 + 사전 성과 통제: 모형 2 + 사전 성과(pre_score)
m3 = smf.ols("perf_score ~ treatment * post + grade_num + tenure + pre_score", data=df).fit()


# ==========================================
# --- 4. DiD 핵심 계수(treatment:post) 추출 ---
# ==========================================
def get_did_results(model):
    """모델에서 DiD 계수(순수 교육 효과)와 p-value를 추출하는 함수"""
    coef = model.params['treatment:post']
    pval = model.pvalues['treatment:post']
    return coef, pval


coef_m1, pval_m1 = get_did_results(m1)
coef_m2, pval_m2 = get_did_results(m2)
coef_m3, pval_m3 = get_did_results(m3)

print("\n[통계 분석 결과: AI 교육의 순수 성과 향상분 (DiD 계수)]")
print(f" - 모형 1 (기본): 향상폭 = {coef_m1:.4f}, p-value = {pval_m1:.4f}")
print(f" - 모형 2 (인적자본 통제): 향상폭 = {coef_m2:.4f}, p-value = {pval_m2:.4f}")
print(f" - 모형 3 (사전성과 통제): 향상폭 = {coef_m3:.4f}, p-value = {pval_m3:.4f}")

# ==========================================
# --- 5. Gemini API를 이용한 결과 자동 해석 ---
# ==========================================
print("\nGemini API를 통해 AI 도입 반대파 설득용 리포트를 작성 중입니다...\n")

prompt = f"""
당신은 뛰어난 데이터 기반 HR 전략가(People Analyst)입니다. 
현재 우리 회사는 AI 활용 교육을 도입하려 하나, 성과 향상에 의구심을 품고 도입을 반대하는 직원들이 많습니다.
반대파를 설득하기 위해 '이중차분법(DiD)' 분석을 수행했으며, 그 결과는 다음과 같습니다.

[DiD 분석 결과 요약]
이중차분법의 교호작용항(treatment:post)은 '시간 흐름에 따른 자연 상승분'을 걷어낸 '순수 AI 교육만의 성과 향상 효과'를 의미합니다.

- 모형 1 (기본 모델): 성과 증가폭 = {coef_m1:.4f}, p-value = {pval_m1:.4f}
- 모형 2 (직급, 근속연수 통제): 성과 증가폭 = {coef_m2:.4f}, p-value = {pval_m2:.4f}
- 모형 3 (직급, 근속연수 + 사전 성과까지 통제): 성과 증가폭 = {coef_m3:.4f}, p-value = {pval_m3:.4f}

위 결과를 바탕으로, AI 교육 도입을 주저하는 임원과 직원들을 설득할 수 있는 "AI 교육 성과 검증 리포트"를 아래 목차에 맞춰 작성해 주세요. (유의수준 0.05 기준)

1. DiD 분석의 신뢰성 어필 (왜 단순 비교가 아닌 이중차분법을 썼으며, 모형 3까지 갈수록 결과가 어떻게 더 정확해졌는지 비전문가도 이해하기 쉽게 비유를 들어 설명)
2. AI 교육의 순수 효과 (자연스러운 성과 향상이나 원래 일을 잘하던 사람의 특성을 걷어냈을 때, AI 교육이 실제로 성과를 얼마나 올렸는지 수치와 통계적 유의성을 바탕으로 확신 있게 제시)
3. 반대파를 향한 데이터 기반 설득 메시지 (정량적 근거를 토대로 AI 교육 전사 도입의 필요성을 강력히 제언)
"""

try:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    print("=" * 70)
    print("🤖 [Gemini AI: AI 교육 성과 검증 및 설득 리포트]")
    print("-" * 70)
    print(response.text.strip())
    print("=" * 70)

except Exception as e:
    print(f"❌ Gemini API 호출 중 오류가 발생했습니다: {e}")