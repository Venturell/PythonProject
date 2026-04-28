import pandas as pd
import numpy as np
import networkx as nx
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. 파일 경로 및 환경 설정 ---
# ==========================================
EXCEL_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"
BASE_DIR = os.path.dirname(EXCEL_PATH)

# 저장 파일명
OUT_COMPARE = os.path.join(BASE_DIR, "2024Q3_조직개편_전후비교.xlsx")
OUT_IT_COMPARE = os.path.join(BASE_DIR, "2024Q3_IT관련_상세비교.xlsx")
OUT_PRE_MAT = os.path.join(BASE_DIR, "2024Q3_Pre_팀매트릭스.xlsx")
OUT_POST_MAT = os.path.join(BASE_DIR, "2024Q3_Post_팀매트릭스.xlsx")

print("데이터를 로드하고 조직개편 전후 분석을 시작합니다...\n")

# ==========================================
# --- 2. 데이터 로드 및 이벤트 검증 ---
# ==========================================
df_emp = pd.read_excel(EXCEL_PATH, sheet_name='employees')
df_edges_raw = pd.read_excel(EXCEL_PATH, sheet_name='edges')

# 이벤트 시트 확인 (없으면 통과)
try:
    df_events = pd.read_excel(EXCEL_PATH, sheet_name='events')
    event_info = df_events[
        (df_events['event_type'] == 'reorganization') &
        (df_events['time_id'] == '2024Q3') &
        (df_events['affected_department'] == 'IT')
        ]
except:
    event_info = pd.DataFrame()

# 직원 매핑 도구
team_map = dict(zip(df_emp['employee_id'], df_emp['team']))
dept_map = dict(zip(df_emp['employee_id'], df_emp['department']))
valid_ids = set(df_emp['employee_id'])

# ==========================================
# --- 3. 데이터 필터링 및 매핑 ---
# ==========================================
# communication, 자기 자신 제외, 유효한 직원
df_filtered = df_edges_raw[
    (df_edges_raw['tie_type'] == 'communication') &
    (df_edges_raw['source'] != df_edges_raw['target']) &
    (df_edges_raw['source'].isin(valid_ids)) &
    (df_edges_raw['target'].isin(valid_ids))
    ].copy()

# 속성 매핑
df_filtered['source_team'] = df_filtered['source'].map(team_map)
df_filtered['target_team'] = df_filtered['target'].map(team_map)
df_filtered['source_department'] = df_filtered['source'].map(dept_map)
df_filtered['target_department'] = df_filtered['target'].map(dept_map)

# Pre / Post 분리 (2024Q3 기준)
REORG_TIME = '2024Q3'
df_pre = df_filtered[df_filtered['time_id'] < REORG_TIME].copy()
df_post = df_filtered[df_filtered['time_id'] >= REORG_TIME].copy()


# ==========================================
# --- 4. 분석 지표 계산 함수 ---
# ==========================================
def calculate_metrics(df_directed):
    if df_directed.empty: return {}

    # 1. Undirected 변환 (node_a, node_b 정렬)
    df_directed['node_a'] = df_directed[['source', 'target']].min(axis=1)
    df_directed['node_b'] = df_directed[['source', 'target']].max(axis=1)
    df_undirected = df_directed.groupby(['node_a', 'node_b']).agg(
        interaction_count=('interaction_count', 'sum'),
        team_a=('source_team', 'first'),  # 동일성 확인용
        team_b=('target_team', 'first')
    ).reset_index()

    # 노드 속성을 가져오기 위해 node_a, node_b 팀 매핑 재적용
    df_undirected['team_a'] = df_undirected['node_a'].map(team_map)
    df_undirected['team_b'] = df_undirected['node_b'].map(team_map)
    df_undirected['is_within'] = df_undirected['team_a'] == df_undirected['team_b']

    # 2. NetworkX 그래프 생성
    G = nx.Graph()
    for _, row in df_emp.iterrows():
        G.add_node(row['employee_id'], team=row['team'])

    for _, row in df_undirected.iterrows():
        G.add_edge(row['node_a'], row['node_b'], weight=row['interaction_count'])

    G_active = G.subgraph([n for n, d in G.degree() if d > 0])  # 고립 노드 제외

    # 3. 기초 지표
    total_ties = len(df_undirected)
    within_ties = df_undirected['is_within'].sum()
    between_ties = total_ties - within_ties

    # 4. 통계 지표
    teams = df_emp['team'].unique()
    team_communities = [set(df_emp[df_emp['team'] == t]['employee_id']) for t in teams]

    detected_comms = list(nx.community.greedy_modularity_communities(G_active, weight='weight')) if len(
        G_active) > 0 else []

    metrics = {
        'number_of_nodes': G_active.number_of_nodes(),
        'number_of_edges': G_active.number_of_edges(),
        'total_ties': total_ties,
        'within_team_ties': within_ties,
        'between_team_ties': between_ties,
        'within_team_ratio': within_ties / total_ties if total_ties > 0 else 0,
        'between_team_ratio': between_ties / total_ties if total_ties > 0 else 0,
        'density': nx.density(G_active) if len(G_active) > 0 else 0,
        'average_degree': np.mean([d for n, d in G_active.degree()]) if len(G_active) > 0 else 0,
        'average_weighted_degree': np.mean([d for n, d in G_active.degree(weight='weight')]) if len(
            G_active) > 0 else 0,
        'team_assortativity': nx.attribute_assortativity_coefficient(G_active, 'team') if len(G_active) > 0 else 0,
        'team_modularity': nx.community.modularity(G, team_communities, weight='weight') if len(G.edges) > 0 else 0,
        'detected_community_modularity': nx.community.modularity(G_active, detected_comms,
                                                                 weight='weight') if detected_comms else 0,
        'num_detected_communities': len(detected_comms)
    }
    return metrics


def calculate_it_metrics(df_directed):
    if df_directed.empty: return {}

    # IT 관련 (Directed 기준)
    it_related = df_directed[(df_directed['source_department'] == 'IT') | (df_directed['target_department'] == 'IT')]
    it_internal = df_directed[(df_directed['source_department'] == 'IT') & (df_directed['target_department'] == 'IT')]
    it_outbound = df_directed[(df_directed['source_department'] == 'IT') & (df_directed['target_department'] != 'IT')]
    it_inbound = df_directed[(df_directed['source_department'] != 'IT') & (df_directed['target_department'] == 'IT')]

    it_related_ties = len(it_related)
    it_cross_dept_ties = len(it_outbound) + len(it_inbound)

    return {
        'it_related_ties': it_related_ties,
        'it_internal_ties': len(it_internal),
        'it_outbound_ties': len(it_outbound),
        'it_inbound_ties': len(it_inbound),
        'it_cross_dept_ties': it_cross_dept_ties,
        'it_internal_ratio': len(it_internal) / it_related_ties if it_related_ties > 0 else 0,
        'it_cross_dept_ratio': it_cross_dept_ties / it_related_ties if it_related_ties > 0 else 0
    }


# ==========================================
# --- 5. 지표 산출 및 통합 ---
# ==========================================
# 전체 요약
pre_metrics = calculate_metrics(df_pre)
post_metrics = calculate_metrics(df_post)

comp_df = pd.DataFrame({'Pre (Before 24Q3)': pre_metrics, 'Post (After 24Q3)': post_metrics})
comp_df['Difference'] = comp_df['Post (After 24Q3)'] - comp_df['Pre (Before 24Q3)']
comp_df = comp_df.round(4).reset_index().rename(columns={'index': 'Indicator'})

# IT 상세
pre_it = calculate_it_metrics(df_pre)
post_it = calculate_it_metrics(df_post)

it_df = pd.DataFrame({'Pre (Before 24Q3)': pre_it, 'Post (After 24Q3)': post_it})
it_df['Difference'] = it_df['Post (After 24Q3)'] - it_df['Pre (Before 24Q3)']
it_df = it_df.round(4).reset_index().rename(columns={'index': 'IT Indicator'})

# 팀-팀 매트릭스 (Directed 기준 interaction_count 합산)
pre_matrix = pd.pivot_table(df_pre, values='interaction_count', index='source_team', columns='target_team',
                            aggfunc='sum', fill_value=0)
post_matrix = pd.pivot_table(df_post, values='interaction_count', index='source_team', columns='target_team',
                             aggfunc='sum', fill_value=0)

# ==========================================
# --- 6. 콘솔 출력 및 판정 ---
# ==========================================
print("=" * 80)
print("1. [분석 기준]")
print(f" - 조직개편 시점(REORG_TIME): {REORG_TIME}")
print(" - 분석 대상: Communication (자기자신 제외, Undirected/Directed 병행)")
print("-" * 80)

print("2. [Events 시트 검증]")
if not event_info.empty:
    print(" ✅ 'reorganization' 이벤트 확인됨 (대상: IT, 시점: 2024Q3)")
else:
    print(" ⚠️ 조건에 일치하는 이벤트가 없으나 분석은 지정된 시점 기준으로 진행합니다.")
print("-" * 80)

print("3. [전체 및 전후 비교 요약 테이블]")
print(comp_df.to_string(index=False))
print("-" * 80)

print("4. [IT 관련 상세 비교]")
print(it_df.to_string(index=False))
print("-" * 80)

print("5. [해석 가이드]")
print(" - between_team_ratio 상승: 부서/팀 간 교류가 증가했음을 의미")
print(" - team_assortativity 감소: '끼리끼리' 뭉치는 현상이 완화됨을 의미")
print(" - team_modularity 감소: 기존 팀 구조의 장벽이 허물어지고 네트워크가 유연해짐을 의미")
print(" - it_cross_dept_ratio 상승: 개편 후 IT 부서가 타 부서와 더 많이 협업하고 있음을 의미")
print("-" * 80)

# 판정 로직 변수 추출
btr_diff = comp_df.loc[comp_df['Indicator'] == 'between_team_ratio', 'Difference'].values[0]
ta_diff = comp_df.loc[comp_df['Indicator'] == 'team_assortativity', 'Difference'].values[0]
tm_diff = comp_df.loc[comp_df['Indicator'] == 'team_modularity', 'Difference'].values[0]
den_diff = comp_df.loc[comp_df['Indicator'] == 'density', 'Difference'].values[0]
it_cross_diff = it_df.loc[it_df['IT Indicator'] == 'it_cross_dept_ratio', 'Difference'].values[0]

# 판정 조건 (감소폭의 경우 Difference가 마이너스이므로 부호 반전하여 판정)
is_changed = (
        (btr_diff > 0.05) or
        (-ta_diff > 0.05) or  # 감소폭 > 0.05
        (-tm_diff > 0.05) or  # 감소폭 > 0.05
        (den_diff > 0.01) or
        (it_cross_diff > 0.05)
)

print("6. [최종 판정]")
if is_changed:
    print(" 💡 [판결]: 하나 이상의 핵심 지표가 유의미하게 변동했습니다. 조직개편 이후 연결 구조가 바뀌었을 가능성이 있습니다.")
else:
    print(" ⚖️ [판결]: 조직개편 전후 연결 구조 변화가 아주 뚜렷하지는 않습니다.")
print("=" * 80)

# ==========================================
# --- 7. 결과 엑셀 저장 ---
# ==========================================
comp_df.to_excel(OUT_COMPARE, index=False)
it_df.to_excel(OUT_IT_COMPARE, index=False)
pre_matrix.to_excel(OUT_PRE_MAT)
post_matrix.to_excel(OUT_POST_MAT)

print(f"\n✅ 4개의 분석 결과 엑셀 파일이 성공적으로 저장되었습니다.\n저장 경로: {BASE_DIR}")