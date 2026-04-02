import pandas as pd
import scipy.stats as stats
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings('ignore')

# --- 1. 데이터 불러오기 ---
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#5\5_PAproject_5_4_rater.xlsx"
df = pd.read_excel(file_path).dropna()

# --- 2. ANOVA 분석 ---
grouped_ratings = [group['rating_score'].values for name, group in df.groupby('rater_id')]
f_stat, p_val = stats.f_oneway(*grouped_ratings)

print(f"--- [3] ANOVA 결과: F={f_stat:.4f}, p-value={p_val:.4f} ---")

# --- 3. HLM (혼합모형) 본 분석 ---
formula = "rating_score ~ C(department) + C(job_level) + performance_true + goal_difficulty + age + tenure_years"
md_full = smf.mixedlm(formula, df, groups=df["rater_id"])
mdf_full = md_full.fit()

print("\n--- [4] HLM 분석 요약 ---")
print(mdf_full.summary())

# --- 4. ICC (Intraclass Correlation Coefficient) 계산 ---
# Null Model(기초 모형)을 통한 ICC 산출
md_null = smf.mixedlm("rating_score ~ 1", df, groups=df["rater_id"])
mdf_null = md_null.fit()
tau_sq = mdf_null.cov_re.iloc[0, 0]
sigma_sq = mdf_null.scale
icc = tau_sq / (tau_sq + sigma_sq)

print(f"\n--- [5] ICC: {icc:.4f} ---")

# --- 5. 평가자별 Random Effect(편향) 추출 및 Bias 분류 ---
re = mdf_full.random_effects
# 추출된 딕셔너리를 데이터프레임으로 변환
re_list = [{'rater_id': k, 'random_effect': v['Group']} for k, v in re.items()]
bias_df = pd.DataFrame(re_list)

# 💡 캡처 이미지 기준(±0.1)으로 관대화/엄격화/중립 분류
def categorize_bias(effect):
    if effect > 0.1:
        return 'Leniency (관대화)'
    elif effect < -0.1:
        return 'Severity (엄격화)'
    else:
        return 'Neutral (중립)'

bias_df['bias_type'] = bias_df['random_effect'].apply(categorize_bias)
bias_df = bias_df.sort_values(by='random_effect', ascending=False)

print("\n--- [6] 평가자별 편향 분석 ---")
print(bias_df.to_string())

# --- 6. 원본 데이터에 편향 반영 및 보정 점수 계산 ---
df = df.merge(bias_df[['rater_id', 'random_effect']], on='rater_id', how='left')
df['adjusted_rating_score'] = df['rating_score'] - df['random_effect']

print("\n--- [7] 보정된 평가 점수 샘플 ---")
# 캡처 화면과 동일한 컬럼만 선택하여 상위 5개 출력
sample_df = df[['employee_id', 'rater_id', 'rating_score', 'random_effect', 'adjusted_rating_score']]
print(sample_df.head().to_string())