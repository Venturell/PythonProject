import pandas as pd
import numpy as np
import networkx as nx
from scipy.stats import pearsonr, spearmanr
import statsmodels.formula.api as smf
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. 파일 경로 및 환경 설정 ---
# ==========================================
EXCEL_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"
BASE_DIR = os.path.dirname(EXCEL_PATH)
OUT_CSV = os.path.join(BASE_DIR, "High_Risk_Brokers.csv")

print("데이터를 로드하고 브로커 과부하(Burnout Risk) 분석을 시작합니다...\n")

# ==========================================
# --- 2. 데이터 로드 및 네트워크 패널 생성 ---
# ==========================================
df_emp = pd.read_excel(EXCEL_PATH, sheet_name='employees')
df_edges = pd.read_excel(EXCEL_PATH, sheet_name='edges')
df_time = pd.read_excel(EXCEL_PATH, sheet_name='employee_time')

valid_ids = set(df_emp['employee_id'])

# Edges 필터링: communication, 자기자신 제외, 유효직원
df_filtered = df_edges[
    (df_edges['tie_type'] == 'communication') &
    (df_edges['source'] != df_edges['target']) &
    (df_edges['source'].isin(valid_ids)) &
    (df_edges['target'].isin(valid_ids))
    ].copy()

time_ids = sorted(df_filtered['time_id'].unique())
panel_data = []

# 시점별 네트워크 지표 계산
for t in time_ids:
    df_t = df_filtered[df_filtered['time_id'] == t].copy()

    # Undirected 변환
    df_t['node_a'] = df_t[['source', 'target']].min(axis=1)
    df_t['node_b'] = df_t[['source', 'target']].max(axis=1)
    df_undirected = df_t.groupby(['node_a', 'node_b'])['interaction_count'].sum().reset_index()

    # Graph 생성
    G = nx.Graph()
    G.add_nodes_from(valid_ids)
    for _, row in df_undirected.iterrows():
        G.add_edge(row['node_a'], row['node_b'], weight=row['interaction_count'])

    deg_dict = dict(G.degree())
    w_deg_dict = dict(G.degree(weight='weight'))
    btwn_dict = nx.betweenness_centrality(G, weight='weight', normalized=True)

    try:
        eigen_dict = nx.eigenvector_centrality(G, weight='weight', max_iter=1000)
    except:
        eigen_dict = nx.eigenvector_centrality_numpy(G, weight='weight')

    for emp in valid_ids:
        panel_data.append({
            'time_id': t,
            'employee_id': emp,
            'degree': deg_dict.get(emp, 0),
            'weighted_degree': w_deg_dict.get(emp, 0),
            'betweenness_centrality': btwn_dict.get(emp, 0),
            'eigenvector_centrality': eigen_dict.get(emp, 0)
        })

df_panel = pd.DataFrame(panel_data)

# ==========================================
# --- 3. 직원 속성 및 Burnout Risk 결합 ---
# ==========================================
emp_cols = ['employee_id', 'name', 'department', 'team', 'job_level', 'is_manager']
df_panel = pd.merge(df_panel, df_emp[emp_cols], on='employee_id', how='left')

df_panel = pd.merge(df_panel, df_time[['time_id', 'employee_id', 'burnout_risk']], on=['time_id', 'employee_id'],
                    how='left')
df_panel = df_panel.dropna(subset=['burnout_risk']).reset_index(drop=True)

# 시차 변수(Lagged Variable) 생성: 다음 시점의 burnout_risk
df_panel = df_panel.sort_values(by=['employee_id', 'time_id']).reset_index(drop=True)
df_panel['next_burnout_risk'] = df_panel.groupby('employee_id')['burnout_risk'].shift(-1)

# ==========================================
# --- 4. 통계 및 회귀 분석 ---
# ==========================================
# 1) 상관분석 (동시점 vs 시차)
pears_sim, p_pears_sim = pearsonr(df_panel['betweenness_centrality'], df_panel['burnout_risk'])
spear_sim, p_spear_sim = spearmanr(df_panel['betweenness_centrality'], df_panel['burnout_risk'])

df_lagged = df_panel.dropna(subset=['next_burnout_risk'])
if not df_lagged.empty:
    pears_lag, p_pears_lag = pearsonr(df_lagged['betweenness_centrality'], df_lagged['next_burnout_risk'])
    spear_lag, p_spear_lag = spearmanr(df_lagged['betweenness_centrality'], df_lagged['next_burnout_risk'])
else:
    pears_lag, p_pears_lag, spear_lag, p_spear_lag = 0, 1, 0, 1

# 2) 회귀분석 (OLS)
# 범주형/문자열 변수가 있을 수 있으므로 C() 처리
reg_formula_sim = "burnout_risk ~ betweenness_centrality + degree + weighted_degree + eigenvector_centrality + C(job_level) + is_manager"
model_sim = smf.ols(reg_formula_sim, data=df_panel).fit()

reg_formula_lag = "next_burnout_risk ~ betweenness_centrality + degree + weighted_degree + eigenvector_centrality + C(job_level) + is_manager"
model_lag = smf.ols(reg_formula_lag, data=df_lagged).fit() if not df_lagged.empty else None

# ==========================================
# --- 5. 고위험 브로커 식별 ---
# ==========================================
btwn_thresh = df_panel['betweenness_centrality'].quantile(0.8)
burn_thresh = df_panel['burnout_risk'].quantile(0.8)

df_panel['high_risk_broker'] = np.where(
    (df_panel['betweenness_centrality'] >= btwn_thresh) &
    (df_panel['burnout_risk'] >= burn_thresh), 1, 0
)

# 가장 최신 시점 혹은 전 기간 통틀어 상위 추출
high_risk_df = df_panel[df_panel['high_risk_broker'] == 1].sort_values(
    by=['time_id', 'burnout_risk', 'betweenness_centrality'], ascending=[False, False, False]
)

# ==========================================
# --- 6. 콘솔 출력 및 판정 ---
# ==========================================
print("=" * 80)
print("1. [분석 기준]")
print(" - 네트워크 단위: Undirected Communication")
print(" - 브로커 부담 지표: Betweenness Centrality (매개 중심성)")
print(" - 결과 지표: Burnout Risk (동시점 및 시차 적용)")
print("-" * 80)

print("2. [상관분석 결과 (Betweenness vs Burnout)]")
print(f" - 동시점(t-t) Pearson 상관계수 : {pears_sim:.4f} (p-value: {p_pears_sim:.4f})")
print(f" - 동시점(t-t) Spearman 상관계수: {spear_sim:.4f} (p-value: {p_spear_sim:.4f})")
print(f" - 시차(t-t+1) Pearson 상관계수 : {pears_lag:.4f} (p-value: {p_pears_lag:.4f})")
print(f" - 시차(t-t+1) Spearman 상관계수: {spear_lag:.4f} (p-value: {p_spear_lag:.4f})")
print("-" * 80)

print("3. [동시점 회귀분석 요약 (Target: burnout_risk)]")
print(
    f" - Betweenness Centrality 계수: {model_sim.params.get('betweenness_centrality', 0):.4f} (p-value: {model_sim.pvalues.get('betweenness_centrality', 1):.4f})")
print(f" - R-squared: {model_sim.rsquared:.4f}")
print("-" * 80)

print("4. [시차 회귀분석 요약 (Target: next_burnout_risk)]")
if model_lag:
    print(
        f" - Betweenness Centrality 계수: {model_lag.params.get('betweenness_centrality', 0):.4f} (p-value: {model_lag.pvalues.get('betweenness_centrality', 1):.4f})")
    print(f" - R-squared: {model_lag.rsquared:.4f}")
else:
    print(" - 시차 데이터 부족으로 회귀분석 불가")
print("-" * 80)

print("5. [고위험 브로커 상위 10건 (상위 20% Betweenness & Burnout)]")
cols_to_show = ['time_id', 'employee_id', 'name', 'department', 'betweenness_centrality', 'burnout_risk']
if not high_risk_df.empty:
    print(high_risk_df[cols_to_show].head(10).to_string(index=False))
else:
    print(" - 조건(상위 20%)을 동시에 만족하는 직원이 없습니다.")
print("-" * 80)

print("6. [해석 가이드]")
print(" - 동시점 분석: '현재 매개 중심성이 높은 사람이 현재 번아웃 점수도 높은가?'를 확인합니다.")
print(" - 시차(Lagged) 분석: '현재 매개 중심성이 높은 사람이 다음 분기에 번아웃 점수가 높아지는가?'를 확인하여 인과성에 가까운 선행성을 분석합니다.")
print(" - 상관분석은 두 변수 1:1 관계이며, 회귀분석은 직급(job_level)이나 매니저 여부(is_manager) 등 통제 변수를 고려한 순수 브로커 효과입니다.")
print("-" * 80)

# 최종 판정 로직
sim_btwn_p = model_sim.pvalues.get('betweenness_centrality', 1)
sim_btwn_coef = model_sim.params.get('betweenness_centrality', 0)
lag_btwn_p = model_lag.pvalues.get('betweenness_centrality', 1) if model_lag else 1
lag_btwn_coef = model_lag.params.get('betweenness_centrality', 0) if model_lag else 0

is_burnout_risk = (
        (p_pears_sim < 0.05 and pears_sim > 0) or
        (p_pears_lag < 0.05 and pears_lag > 0) or
        (sim_btwn_p < 0.05 and sim_btwn_coef > 0) or
        (lag_btwn_p < 0.05 and lag_btwn_coef > 0)
)

print("7. [최종 판정]")
if is_burnout_risk:
    print(" 🚨 [판결]: 브로커 부담이 높은 직원은 burnout risk가 높을 가능성이 있습니다.")
else:
    print(" ⚖️ [판결]: 브로커 부담과 burnout risk 간의 뚜렷한 양(+)의 관계는 강하지 않을 수 있습니다.")
print("=" * 80)

# ==========================================
# --- 7. 결과 저장 ---
# ==========================================
high_risk_df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
print(f"\n✅ 고위험 브로커 목록이 CSV로 저장되었습니다.\n경로: {OUT_CSV}")