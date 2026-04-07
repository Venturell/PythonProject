import pandas as pd
import numpy as np
import scipy.stats as stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings('ignore')  # 분석에 지장 없는 수렴 경고 숨김

# ==========================================
# --- 1. 파일 경로 설정 (경로 오류 완벽 해결) ---
# ==========================================
# 데이터 불러오기 경로
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#5\5_PAproject_5_4_rater.xlsx"

# 엑셀 결과 저장 경로 (동일한 폴더에 'Result' 이름으로 저장)
output_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#5\5_PAproject_5_4_rater_Result.xlsx"

print("데이터를 불러오고 전처리를 시작합니다...")
df = pd.read_excel(file_path)
df = df.dropna()

# ==========================================
# --- 2. 기술통계 (Descriptive Statistics) ---
# ==========================================
desc_stats = df.describe()
print("\n--- [2] 기술 통계 요약 ---")
print(desc_stats[['performance_true', 'rating_score']].head().to_string())

# ==========================================
# --- 3. ANOVA: 평가자 간 점수 평균 차이 ---
# ==========================================
grouped_ratings = [group['rating_score'].values for name, group in df.groupby('rater_id')]
f_stat, p_val = stats.f_oneway(*grouped_ratings)

print(f"\n--- [3] ANOVA 결과: F={f_stat:.4f}, p-value={p_val:.4f} ---")

# ==========================================
# --- 4. HLM (혼합모형) 본 분석 ---
# ==========================================
# 실제 성과 및 기타 통제변수를 반영한 다층모형 적합
formula = "rating_score ~ performance_true + goal_difficulty + C(department) + C(job_level) + age + tenure_years"
md_full = smf.mixedlm(formula, df, groups=df["rater_id"])
mdf_full = md_full.fit()

print("\n--- [4] HLM 분석 요약 ---")
print(mdf_full.summary())

# ==========================================
# --- 5. ICC (Intraclass Correlation) 계산 ---
# ==========================================
# 통제변수 없는 Null Model로 계산
md_null = smf.mixedlm("rating_score ~ 1", df, groups=df["rater_id"])
mdf_null = md_null.fit()

tau_sq = mdf_null.cov_re.iloc[0, 0]  # 평가자 간 분산
sigma_sq = mdf_null.scale  # 평가자 내 분산
icc = tau_sq / (tau_sq + sigma_sq)

print(f"\n--- [5] ICC: {icc:.4f} ---")

# ==========================================
# --- 6. 평가자별 Random Effect(편향) 추출 ---
# ==========================================
re = mdf_full.random_effects
rater_bias = {k: v['Group'] for k, v in re.items()}

bias_df = pd.DataFrame(list(rater_bias.items()), columns=['rater_id', 'random_effect'])


# 편향 기준에 따른 테이블 생성 (+0.1 이상 관대화, -0.1 이하 엄격화)
def categorize_bias(score):
    if score >= 0.1:
        return 'Leniency (관대화)'
    elif score <= -0.1:
        return 'Severity (엄격화)'
    else:
        return 'Neutral (중립)'


bias_df['bias_type'] = bias_df['random_effect'].apply(categorize_bias)
bias_df = bias_df.sort_values(by='random_effect', ascending=False).reset_index(drop=True)

print("\n--- [6] 평가자별 편향 분석 ---")
print(bias_df.to_string())

# ==========================================
# --- 7. 최종 평가점수 보정값 계산 ---
# ==========================================
df = df.merge(bias_df[['rater_id', 'random_effect', 'bias_type']], on='rater_id', how='left')

# 기존 점수에서 평가자의 편향(random_effect) 거품을 빼줌
df['adjusted_rating_score'] = df['rating_score'] - df['random_effect']

print("\n--- [7] 보정된 평가 점수 샘플 ---")
sample_df = df[['employee_id', 'rater_id', 'rating_score', 'random_effect', 'adjusted_rating_score']]
print(sample_df.head().to_string())

# ==========================================
# --- 8. 분석 결과를 엑셀로 저장 ---
# ==========================================
print(f"\n분석 결과를 엑셀 파일로 저장 중입니다...")

try:
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 1. 종합 데이터 (보정 점수 포함)
        df.to_excel(writer, sheet_name='1. Adjusted_Dataset', index=False)

        # 2. 평가자 편향 테이블
        bias_df.to_excel(writer, sheet_name='2. Rater_Bias_Summary', index=False)

        # 3. 모델 성능 지표 (ICC 및 ANOVA)
        pd.DataFrame({'Metric': ['ICC', 'ANOVA_F_stat', 'ANOVA_p_val'],
                      'Value': [icc, f_stat, p_val]}).to_excel(writer, sheet_name='3. Model_Metrics', index=False)

        # 4. HLM 모형 요약 결과
        summary_df = pd.DataFrame([mdf_full.summary().as_text()], columns=['HLM_Summary'])
        summary_df.to_excel(writer, sheet_name='4. HLM_Summary', index=False)

    print(f"✅ 엑셀 파일 저장 성공! \n저장 경로: {output_path}")

except Exception as e:
    print(f"❌ 엑셀 저장 중 오류가 발생했습니다: {e}")
    print("해당 엑셀 파일이 이미 열려있다면 종료 후 다시 실행해 주세요.")