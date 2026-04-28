import pandas as pd
import numpy as np
import networkx as nx
import os
import warnings

warnings.filterwarnings('ignore')

# 동적 사회 분석 - 신규 프로젝트 이후 협업이 증가했는가?
# ==========================================
# --- 1. 파일 경로 및 환경 설정 ---
# ==========================================
EXCEL_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"
BASE_DIR = os.path.dirname(EXCEL_PATH)

# 저장 파일명
OUT_COMPARE = os.path.join(BASE_DIR, "2025Q1_신규프로젝트_전후비교.csv")
OUT_PRE_TEAM_MAT = os.path.join(BASE_DIR, "2025Q1_Pre_팀협업매트릭스.csv")
OUT_POST_TEAM_MAT = os.path.join(BASE_DIR, "2025Q1_Post_팀협업매트릭스.csv")
OUT_PRE_DEPT_MAT = os.path.join(BASE_DIR, "2025Q1_Pre_부서협업매트릭스.csv")
OUT_POST_DEPT_MAT = os.path.join(BASE_DIR, "2025Q1_Post_부서협업매트릭스.csv")

print("데이터를 로드하고 신규 프로젝트 전후 분석을 시작합니다...\n")

# ==========================================
# --- 2. 데이터 로드 및 이벤트 검증 ---
# ==========================================
df_emp = pd.read_excel(EXCEL_PATH, sheet_name='employees')
df_edges_raw = pd.read_excel(EXCEL_PATH, sheet_name='edges')

# 이벤트 시트 확인
try:
    df_events = pd.read_excel(EXCEL_PATH, sheet_name='events')
    event_info = df_events[
        (df_events['event_type'] == 'new_project') &
        (df_events['time_id'] == '2025Q1') &
        (df_events['affected_department'] == 'All')
        ]
except:
    event_info = pd.DataFrame()

# ==========================================
# --- 3. 데이터 필터링 및 매핑 ---
# ==========================================
valid_ids = set(df_emp['employee_id'])

# collaboration, 자기 자신 제외, 유효한 직원
df_filtered = df_edges_raw[
    (df_edges_raw['tie_type'] == 'collaboration') &
    (df_edges_raw['source'] != df_edges_raw['target']) &
    (df_edges_raw['source'].isin(valid_ids)) &
    (df_edges_raw['target'].isin(valid_ids))
    ].copy()

# 속성 매핑
team_map = dict(zip(df_emp['employee_id'], df_emp['team']))
dept_map = dict(zip(df_emp['employee_id'], df_emp['department']))

df_filtered['source_team'] = df_filtered['source'].map(team_map)
df_filtered['target_team'] = df_filtered['target'].map(team_map)
df_filtered['source_department'] = df_filtered['source'].map(dept_map)
df_filtered['target_department'] = df_filtered['target'].map(dept_map)

# Pre / Post 분리
PROJECT_START_TIME = '2025Q1'
df_pre = df_filtered[df_filtered['time_id'] < PROJECT_START_TIME].copy()
df_post = df_filtered[df_filtered['time_id'] >= PROJECT_START_TIME].copy()


# ==========================================
# --- 4. 분석 지표 계산 함수 ---
# ==========================================
def calculate_metrics(df_directed):
    if df_directed.empty: return {}

    # 1. Undirected 변환 (정렬 후 합산)
    df_directed['node_a'] = df_directed[['source', 'target']].min(axis=1)
    df_directed['node_b'] = df_directed[['source', 'target']].max(axis=1)
    df_undirected = df_directed.groupby(['node_a', 'node_b'])['interaction_count'].sum().reset_index()

    # 속성 재매핑
    df_undirected['team_a'] = df_undirected['node_a'].map(team_map)
    df_undirected['team_b'] = df_undirected['node_b'].map(team_map)
    df_undirected['dept_a'] = df_undirected['node_a'].map(dept_map)
    df_undirected['dept_b'] = df_undirected['node_b'].map(dept_map)

    # 2. NetworkX 그래프 생성
    G = nx.Graph()
    for _, row in df_emp.iterrows():
        G.add_node(row['employee_id'], team=row['team'], department=row['department'])
    for _, row in df_undirected.iterrows():
        G.add_edge(row['node_a'], row['node_b'], weight=row['interaction_count'])

    G_active = G.subgraph([n for n, d in G.degree() if d > 0])  # 고립 노드 제외

    # 3. Tie 계산
    total_ties = len(df_undirected)
    within_team_ties = (df_undirected['team_a'] == df_undirected['team_b']).sum()
    between_team_ties = total_ties - within_team_ties
    within_dept_ties = (df_undirected['dept_a'] == df_undirected['dept_b']).sum()
    between_dept_ties = total_ties - within_dept_ties

    # 4. Modularity용 Community 구성
    teams = df_emp['team'].unique()
    depts = df_emp['department'].unique()
    team_comms = [set(df_emp[df_emp['team'] == t]['employee_id']) for t in teams]
    dept_comms = [set(df_emp[df_emp['department'] == d]['employee_id']) for d in depts]
    detected_comms = list(nx.community.greedy_modularity_communities(G_active, weight='weight')) if len(
        G_active) > 0 else []

    # 5. 지표 딕셔너리
    metrics = {
        'number_of_nodes': G_active.number_of_nodes(),
        'number_of_edges': G_active.number_of_edges(),
        'total_ties': total_ties,
        'within_team_ties': within_team_ties,
        'between_team_ties': between_team_ties,
        'within_team_ratio': within_team_ties / total_ties if total_ties > 0 else 0,
        'between_team_ratio': between_team_ties / total_ties if total_ties > 0 else 0,
        'within_department_ties': within_dept_ties,
        'between_department_ties': between_dept_ties,
        'within_department_ratio': within_dept_ties / total_ties if total_ties > 0 else 0,
        'between_department_ratio': between_dept_ties / total_ties if total_ties > 0 else 0,
        'density': nx.density(G_active) if len(G_active) > 0 else 0,
        'average_degree': np.mean([d for n, d in G_active.degree()]) if len(G_active) > 0 else 0,
        'average_weighted_degree': np.mean([d for n, d in G_active.degree(weight='weight')]) if len(
            G_active) > 0 else 0,
        'team_assortativity': nx.attribute_assortativity_coefficient(G_active, 'team') if len(G_active) > 0 else 0,
        'department_assortativity': nx.attribute_assortativity_coefficient(G_active, 'department') if len(
            G_active) > 0 else 0,
        'team_modularity': nx.community.modularity(G, team_comms, weight='weight') if len(G.edges) > 0 else 0,
        'department_modularity': nx.community.modularity(G, dept_comms, weight='weight') if len(G.edges) > 0 else 0,
        'detected_community_modularity': nx.community.modularity(G_active, detected_comms,
                                                                 weight='weight') if detected_comms else 0,
        'num_detected_communities': len(detected_comms)
    }
    return metrics


# ==========================================
# --- 5. 지표 산출 및 통합 ---
# ==========================================
pre_metrics = calculate_metrics(df_pre)
post_metrics = calculate_metrics(df_post)

comp_df = pd.DataFrame({'Pre (Before 25Q1)': pre_metrics, 'Post (After 25Q1)': post_metrics})
comp_df['Difference'] = comp_df['Post (After 25Q1)'] - comp_df['Pre (Before 25Q1)']
comp_df = comp_df.round(4).reset_index().rename(columns={'index': 'Indicator'})

# 핵심 비교 추출
core_indicators = ['total_ties', 'between_team_ratio', 'between_department_ratio', 'density', 'average_degree']
core_comp_df = comp_df[comp_df['Indicator'].isin(core_indicators)]

# 매트릭스 생성 (Directed Raw Data 기준 Sum)
pre_team_mat = pd.pivot_table(df_pre, values='interaction_count', index='source_team', columns='target_team',
                              aggfunc='sum', fill_value=0)
post_team_mat = pd.pivot_table(df_post, values='interaction_count', index='source_team', columns='target_team',
                               aggfunc='sum', fill_value=0)
pre_dept_mat = pd.pivot_table(df_pre, values='interaction_count', index='source_department',
                              columns='target_department', aggfunc='sum', fill_value=0)
post_dept_mat = pd.pivot_table(df_post, values='interaction_count', index='source_department',
                               columns='target_department', aggfunc='sum', fill_value=0)

# ==========================================
# --- 6. 콘솔 출력 및 판정 ---
# ==========================================
print("=" * 80)
print("1. [분석 기준]")
print(f" - 신규 프로젝트 시점: {PROJECT_START_TIME}")
print(" - 분석 대상: Collaboration 네트워크 (자기자신 제외, Undirected 집계 및 통계)")
print("-" * 80)

print("2. [Events 시트 검증 (신규 프로젝트)]")
if not event_info.empty:
    print(" ✅ 'new_project' 이벤트 확인됨 (대상: All, 시점: 2025Q1)")
else:
    print(" ⚠️ 조건에 일치하는 이벤트가 없으나 분석은 지정된 시점 기준으로 진행합니다.")
print("-" * 80)

print("3. [전체 요약] & 4. [전후 비교 테이블]")
print(comp_df.to_string(index=False))
print("-" * 80)

print("5. [협업 증가 관련 핵심 비교]")
print(core_comp_df.to_string(index=False))
print("-" * 80)

print("6~9. [매트릭스 안내]")
print(" - Pre/Post 시점의 팀별, 부서별 협업 매트릭스가 성공적으로 생성되었습니다. (CSV 파일 참조)")
print("-" * 80)

print("10. [해석 가이드]")
print(" - total_ties 및 density 증가: 조직 내 전반적인 협업량이 늘어났음을 의미합니다.")
print(" - between_team/department_ratio 상승: 사일로 현상이 타파되고 부서 간 교류가 활성화되었음을 의미합니다.")
print(" - average_degree 증가: 1인당 평균적으로 협업하는 동료의 수가 늘어났음을 뜻합니다.")
print("-" * 80)

# 최종 판정 로직
diff_total_ties = core_comp_df.loc[core_comp_df['Indicator'] == 'total_ties', 'Difference'].values[0]
diff_btr = core_comp_df.loc[core_comp_df['Indicator'] == 'between_team_ratio', 'Difference'].values[0]
diff_bdr = core_comp_df.loc[core_comp_df['Indicator'] == 'between_department_ratio', 'Difference'].values[0]
diff_den = core_comp_df.loc[core_comp_df['Indicator'] == 'density', 'Difference'].values[0]
diff_avg_deg = core_comp_df.loc[core_comp_df['Indicator'] == 'average_degree', 'Difference'].values[0]

is_increased = (
        (diff_total_ties > 0) or
        (diff_btr > 0.05) or
        (diff_bdr > 0.05) or
        (diff_den > 0.01) or
        (diff_avg_deg > 0.5)
)

print("11. [최종 판정]")
if is_increased:
    print(" 💡 [판결]: 하나 이상의 핵심 지표가 유의미하게 변동했습니다. 신규 프로젝트 이후 협업이 증가했을 가능성이 있습니다.")
else:
    print(" ⚖️ [판결]: 신규 프로젝트 전후 협업 증가가 아주 뚜렷하지는 않습니다.")
print("=" * 80)

# ==========================================
# --- 7. 결과 CSV 저장 ---
# ==========================================
comp_df.to_csv(OUT_COMPARE, index=False, encoding='utf-8-sig')
pre_team_mat.to_csv(OUT_PRE_TEAM_MAT, encoding='utf-8-sig')
post_team_mat.to_csv(OUT_POST_TEAM_MAT, encoding='utf-8-sig')
pre_dept_mat.to_csv(OUT_PRE_DEPT_MAT, encoding='utf-8-sig')
post_dept_mat.to_csv(OUT_POST_DEPT_MAT, encoding='utf-8-sig')

print(f"\n✅ 5개의 분석 결과 CSV 파일이 성공적으로 저장되었습니다.\n저장 경로: {BASE_DIR}")