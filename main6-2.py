import pandas as pd
import scipy.stats as stats
import pingouin as pg
from google import genai
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. Gemini API 설정 ---
# ==========================================
# 🚨 여기에 Google AI Studio에서 발급받은 API 키를 입력하세요!
API_KEY = "AIzaSyCM8d4o1QMn7N2ITHYHoqAqyns6s49eutI"
client = genai.Client(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash'

# ==========================================
# --- 2. 데이터 불러오기 ---
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#6\6_PAproject_6_2_Leadership.xlsx"

print("데이터를 불러오고 전처리를 시작합니다...")
df = pd.read_excel(file_path)

# 결측치 제거
df = df.dropna(subset=['Employee_Group', 'Pre_Training_Score', 'Post_Training_Score'])

# 그룹 분리
group_yes = df[df['Employee_Group'] == 'yes']['Post_Training_Score']
group_no = df[df['Employee_Group'] == 'no']['Post_Training_Score']

mean_yes = group_yes.mean()
mean_no = group_no.mean()

print(f"\n[기초 통계]")
print(f" - 교육 참석(yes) 사후 점수 평균: {mean_yes:.2f}점")
print(f" - 교육 미참석(no) 사후 점수 평균: {mean_no:.2f}점")

# ==========================================
# --- 3. 통계 분석: ANOVA vs ANCOVA ---
# ==========================================
# 1) ANOVA (사전 점수 무시, 사후 점수만 비교)
f_stat_anova, p_val_anova = stats.f_oneway(group_yes, group_no)

# 2) ANCOVA (사전 점수를 통제한 사후 점수 비교)
ancova_result = pg.ancova(data=df, dv='Post_Training_Score', between='Employee_Group', covar='Pre_Training_Score')

# [🚨 수정된 부분] pingouin 버전에 상관없이 p-value 컬럼을 자동으로 찾기
f_stat_ancova = ancova_result.loc[ancova_result['Source'] == 'Employee_Group', 'F'].values[0]

# 컬럼명에 'p-unc', 'p-val', 'p_value' 등 p로 시작하는 컬럼(편태제곱 np2 제외)을 자동 식별
p_col = [col for col in ancova_result.columns if col.startswith('p') and col != 'np2'][0]
p_val_ancova = ancova_result.loc[ancova_result['Source'] == 'Employee_Group', p_col].values[0]

print(f"\n[통계 분석 결과]")
print(f" 1. ANOVA 결과: F = {f_stat_anova:.4f}, p-value = {p_val_anova:.4f}")
print(f" 2. ANCOVA 결과: F = {f_stat_ancova:.4f}, p-value = {p_val_ancova:.4f}")

# ==========================================
# --- 4. Gemini API를 이용한 결과 자동 해석 ---
# ==========================================
print("\nGemini API를 통해 두 통계 결과를 비교 해석 중입니다...\n")

prompt = f"""
당신은 최고 수준의 HR 데이터 애널리스트입니다.
우리 회사는 리더십 교육의 효과를 검증하기 위해 두 가지 통계 분석을 실시했습니다.

[상황 설명]
- 교육 만족도는 매우 높았으나, 단순히 교육 후 점수만 비교했을 때는 교육 효과가 애매하게 나왔습니다.
- 이에 "직원들이 원래 가지고 있던 리더십 역량(사전 점수)의 차이가 분석을 왜곡한 것은 아닐까?"라는 가설을 세웠습니다.

[데이터 결과]
1. ANOVA (사전 점수 무시하고 사후 점수만 비교): p-value = {p_val_anova:.4f}
2. ANCOVA (사전 점수를 통제하고 사후 점수 비교): p-value = {p_val_ancova:.4f}
- 유의수준은 0.05 기준입니다.

위 결과를 바탕으로 경영진(C-level)에게 보고할 "교육 효과 분석 결과"를 다음 목차에 맞춰 작성해 주세요.
(전문적인 통계 용어를 쓰되, 비전문가도 완벽하게 이해할 수 있도록 쉽게 비유하여 설명하세요.)

1. 팩트 요약: 두 분석 결과(p-value)의 차이점이 무엇인가?
2. 통계의 마법 해석: 왜 ANOVA에서는 효과가 없다고 나왔는데, ANCOVA에서는 다른 결과가 나왔는가? (개인차/사전 점수의 '노이즈' 개념을 활용하여 설명)
3. 최종 결론 및 HR 제언: 그래서 이 교육은 진짜 효과가 있었는가? 앞으로 교육 평가는 어떻게 해야 하는가?
"""

try:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    print("=" * 60)
    print("🤖 [Gemini AI: ANOVA vs ANCOVA 비교 분석 리포트]")
    print("-" * 60)
    print(response.text.strip())
    print("=" * 60)

except Exception as e:
    print(f"❌ Gemini API 호출 중 오류가 발생했습니다: {e}")