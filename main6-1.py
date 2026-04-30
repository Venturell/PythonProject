import pandas as pd
import scipy.stats as stats
from google import genai
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. Gemini API 설정 ---
# ==========================================
# 🚨 여기에 Google AI Studio에서 발급받은 API 키를 입력하세요!
API_KEY = "AIz잼민이api키입력"
client = genai.Client(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash'

# ==========================================
# --- 2. 데이터 불러오기 ---
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#6\6_PAproject_6_2_Leadership.xlsx"

print("데이터를 불러오고 전처리를 시작합니다...")
df = pd.read_excel(file_path)

# 결측치 제거 (분석 대상 컬럼만)
df = df.dropna(subset=['Employee_Group', 'Post_Training_Score'])

# 그룹별 데이터 분리 ('yes' 그룹과 'no' 그룹)
group_yes = df[df['Employee_Group'] == 'yes']['Post_Training_Score']
group_no = df[df['Employee_Group'] == 'no']['Post_Training_Score']

mean_yes = group_yes.mean()
mean_no = group_no.mean()

print(f"\n[기초 통계]")
print(f" - 교육 참석 그룹(yes) 평균 사후 점수: {mean_yes:.2f}점")
print(f" - 교육 미참석 그룹(no) 평균 사후 점수: {mean_no:.2f}점")

# ==========================================
# --- 3. 일원 분산 분석 (One-way ANOVA) ---
# ==========================================
f_stat, p_val = stats.f_oneway(group_yes, group_no)

print(f"\n[ANOVA 검증 결과]")
print(f" - F-통계량: {f_stat:.4f}")
print(f" - p-value: {p_val:.4f}")

# ==========================================
# --- 4. Gemini API를 이용한 자동 해석 ---
# ==========================================
print("\nGemini API를 통해 분석 결과를 경영진 보고용으로 해석 중입니다...\n")

# AI에게 상황과 데이터를 설명하고 해석을 지시하는 프롬프트
prompt = f"""
당신은 기업의 피플애널리틱스(HR 데이터 분석) 전문가입니다. 
우리 회사는 사원/대리를 대상으로 리더십 교육을 진행했고, 교육 만족도는 90점 이상으로 매우 높았습니다.
하지만 경영진은 "만족도 말고, 실제 리더십 역량(점수)이 향상되었는지 통계적으로 증명하라"고 요구하고 있습니다.

이에 따라 교육 참석 그룹(yes)과 미참석 그룹(no)의 교육 후 점수(Post_Training_Score)를 비교하는 ANOVA 분석을 실시했습니다.
- 참석 그룹 평균: {mean_yes:.2f}점
- 미참석 그룹 평균: {mean_no:.2f}점
- 통계 분석 결과: F-값 = {f_stat:.4f}, p-value = {p_val:.4f}

위 데이터를 바탕으로 경영진(C-level)에게 보고할 수 있도록 다음 형식에 맞춰 결과를 해석해 주세요.
(유의수준 0.05를 기준으로 p-value를 판단하세요.)

1. 분석 결과 요약 (1~2문장)
2. 통계적 의미 해석 (왜 이런 결론이 나왔는지 쉽게 설명)
3. HR 전략적 제언 (만족도는 높으나 실제 효과는 어떠한지 종합하여 제언)
"""

try:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    print("=" * 60)
    print("🤖 [Gemini AI 데이터 해석 결과]")
    print("-" * 60)
    print(response.text.strip())
    print("=" * 60)

except Exception as e:
    print(f"❌ Gemini API 호출 중 오류가 발생했습니다: {e}")