import pandas as pd
import numpy as np
import networkx as nx
from networkx.algorithms import community
import os

# ==========================================
# 1. 환경 설정 및 데이터 불러오기
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"
base_dir = os.path.dirname(file_path)

print("데이터를 불러오는 중입니다...")
employees = pd.read_excel(file_path, sheet_name='employees')
edges = pd.read_excel(file_path, sheet_name='edges')
events = pd.read_excel(file_path, sheet_name='events')

# ==========================================
# 2. 이벤트 확인
# ==========================================
PROJECT_START_TIME = "2025Q1"
event_check = events[
    (events['event_type'] == 'new_project') &
    (events['time_id'] == PROJECT_START_TIME) &
    (events['affected_department'] == 'All')
    ]

print("\n" + "=" * 50)
print("[1] 분석 기준 및 [2] 이벤트 확인")
print("=" * 50)
print(f"기준 시점(PROJECT_START_TIME): {PROJECT_START_TIME}")
print("비교 그룹: pre (2025Q1 이전) vs post (2025Q1 이후)")
if not event_check.empty:
    print(f"✓ events 시트에서 '{PROJECT_START_TIME}' 신규 프로젝트 시작 이벤트를 확인했습니다.")
else:
    print(f"⚠ events 시트에서 조건에 맞는 이벤트를 찾지 못했습니다. (지정된 기준으로 분석은 계속 진행합니다.)")

# ==========================================
# 3. 데이터 전처리
# ==========================================
edges = edges[edges['tie_type'] == 'collaboration'].copy()
edges = edges[edges['source'] != edges['target']].copy()

valid_employees = set(employees['employee_id'])
edges = edges[edges['source'].isin(valid_employees) & edges['target'].isin(valid_employees)].copy()

emp_info = employees.set_index('employee_id')[['team', 'department']].to_dict('index')

edges['source_team'] = edges['source'].map(lambda x: emp_info[x]['team'])
edges['target_team'] = edges['target'].map(lambda x: emp_info[x]['team'])
edges['source_department'] = edges['source'].map(lambda x: emp_info[x]['department'])
edges['target_department'] = edges['target'].map(lambda x: emp_info[x]['department'])

edges['node1'] = np.where(edges['source'] < edges['target'], edges['source'], edges['target'])
edges['node2'] = np.where(edges['source'] < edges['target'], edges['target'], edges['source'])

edges_agg = edges.groupby(['time_id', 'node1', 'node2']).agg(
    interaction_count=('interaction_count', 'sum')
).reset_index()

edges_agg['node1_team'] = edges_agg['node1'].map(lambda x: emp_info[x]['team'])
edges_agg['node2_team'] = edges_agg['node2'].map(lambda x: emp_info[x]['team'])
edges_agg['node1_department'] = edges_agg['node1'].map(lambda x: emp_info[x]['department'])
edges_agg['node2_department'] = edges_agg['node2'].map(lambda x: emp_info[x]['department'])

edges_agg['is_within_team'] = edges_agg['node1_team'] == edges_agg['node2_team']
edges_agg['is_within_department'] = edges_agg['node1_department'] == edges_agg['node2_department']

edges_pre = edges_agg[edges_agg['time_id'] < PROJECT_START_TIME].copy()
edges_post = edges_agg[edges_agg['time_id'] >= PROJECT_START_TIME].copy()


# ==========================================
# 4. 분석 함수 정의
# ==========================================
def analyze_network(df_edges, employees_df):
    if df_edges.empty:
        return None, None

    G = nx.Graph()

    for _, row in employees_df.iterrows():
        G.add_node(row['employee_id'], team=row['team'], department=row['department'])

    df_grouped = df_edges.groupby(['node1', 'node2', 'is_within_team', 'is_within_department']).agg(
        weight=('interaction_count', 'sum')
    ).reset_index()

    for _, row in df_grouped.iterrows():
        G.add_edge(row['node1'], row['node2'], weight=row['weight'])

    G.remove_nodes_from(list(nx.isolates(G)))

    if len(G.nodes()) == 0:
        return None, None

    number_of_nodes = G.number_of_nodes()
    number_of_edges = G.number_of_edges()
    total_ties = df_grouped['weight'].sum()

    within_team_ties = df_grouped[df_grouped['is_within_team']]['weight'].sum()
    between_team_ties = df_grouped[~df_grouped['is_within_team']]['weight'].sum()
    within_team_ratio = within_team_ties / total_ties if total_ties > 0 else 0
    between_team_ratio = between_team_ties / total_ties if total_ties > 0 else 0

    within_dept_ties = df_grouped[df_grouped['is_within_department']]['weight'].sum()
    between_dept_ties = df_grouped[~df_grouped['is_within_department']]['weight'].sum()
    within_dept_ratio = within_dept_ties / total_ties if total_ties > 0 else 0
    between_dept_ratio = between_dept_ties / total_ties if total_ties > 0 else 0

    density = nx.density(G)
    degrees = [d for n, d in G.degree()]
    average_degree = np.mean(degrees) if degrees else 0
    weighted_degrees = [d for n, d in G.degree(weight='weight')]
    average_weighted_degree = np.mean(weighted_degrees) if weighted_degrees else 0

    try:
        team_assortativity = nx.attribute_assortativity_coefficient(G, 'team')
    except:
        team_assortativity = np.nan

    try:
        department_assortativity = nx.attribute_assortativity_coefficient(G, 'department')
    except:
        department_assortativity = np.nan

    def get_modularity(attr_name):
        attr_dict = nx.get_node_attributes(G, attr_name)
        groups = set(attr_dict.values())
        communities = [[n for n, a in attr_dict.items() if a == g] for g in groups]
        communities = [c for c in communities if len(c) > 0]
        try:
            return nx.algorithms.community.modularity(G, communities, weight='weight')
        except:
            return np.nan

    team_modularity = get_modularity('team')
    department_modularity = get_modularity('department')

    try:
        detected_comms = community.louvain_communities(G, weight='weight')
        num_detected_communities = len(detected_comms)
        detected_community_modularity = community.modularity(G, detected_comms, weight='weight')
    except:
        num_detected_communities = np.nan
        detected_community_modularity = np.nan

    metrics = {
        'number_of_nodes': number_of_nodes,
        'number_of_edges': number_of_edges,
        'total_ties': total_ties,
        'within_team_ties': within_team_ties,
        'between_team_ties': between_team_ties,
        'within_team_ratio': within_team_ratio,
        'between_team_ratio': between_team_ratio,
        'within_department_ties': within_dept_ties,
        'between_department_ties': between_dept_ties,
        'within_department_ratio': within_dept_ratio,
        'between_department_ratio': between_dept_ratio,
        'density': density,
        'average_degree': average_degree,
        'average_weighted_degree': average_weighted_degree,
        'team_assortativity': team_assortativity,
        'department_assortativity': department_assortativity,
        'team_modularity': team_modularity,
        'department_modularity': department_modularity,
        'detected_community_modularity': detected_community_modularity,
        'num_detected_communities': num_detected_communities
    }

    return metrics, df_grouped


def make_matrix(df_grouped, attr1, attr2, employees_df, attr_name):
    df_sym1 = df_grouped[[attr1, attr2, 'weight']].rename(columns={attr1: 'source', attr2: 'target'})
    df_sym2 = df_grouped[[attr2, attr1, 'weight']].rename(columns={attr2: 'source', attr1: 'target'})
    df_sym = pd.concat([df_sym1, df_sym2]).groupby(['source', 'target'])['weight'].sum().reset_index()

    unique_attrs = sorted(employees_df[attr_name].dropna().unique())
    matrix = df_sym.pivot(index='source', columns='target', values='weight').reindex(index=unique_attrs,
                                                                                     columns=unique_attrs).fillna(0)

    for attr in unique_attrs:
        matrix.loc[attr, attr] = matrix.loc[attr, attr] / 2

    return matrix


# ==========================================
# 5. 분석 수행 및 매트릭스 생성
# ==========================================
pre_metrics, pre_grouped = analyze_network(edges_pre, employees)
post_metrics, post_grouped = analyze_network(edges_post, employees)

df_compare = pd.DataFrame([pre_metrics, post_metrics], index=['Pre (이전)', 'Post (이후)']).T
df_compare['Diff (증감)'] = df_compare['Post (이후)'] - df_compare['Pre (이전)']


def add_attributes_to_grouped(grouped):
    if grouped is not None:
        grouped['node1_team'] = grouped['node1'].map(lambda x: emp_info[x]['team'])
        grouped['node2_team'] = grouped['node2'].map(lambda x: emp_info[x]['team'])
        grouped['node1_department'] = grouped['node1'].map(lambda x: emp_info[x]['department'])
        grouped['node2_department'] = grouped['node2'].map(lambda x: emp_info[x]['department'])
    return grouped


pre_grouped = add_attributes_to_grouped(pre_grouped)
post_grouped = add_attributes_to_grouped(post_grouped)

pre_team_matrix = make_matrix(pre_grouped, 'node1_team', 'node2_team', employees,
                              'team') if pre_grouped is not None else pd.DataFrame()
post_team_matrix = make_matrix(post_grouped, 'node1_team', 'node2_team', employees,
                               'team') if post_grouped is not None else pd.DataFrame()

pre_dept_matrix = make_matrix(pre_grouped, 'node1_department', 'node2_department', employees,
                              'department') if pre_grouped is not None else pd.DataFrame()
post_dept_matrix = make_matrix(post_grouped, 'node1_department', 'node2_department', employees,
                               'department') if post_grouped is not None else pd.DataFrame()

# ==========================================
# 6. 최종 판정 로직
# ==========================================
diff_total_ties = df_compare.loc['total_ties', 'Diff (증감)']
diff_between_team_ratio = df_compare.loc['between_team_ratio', 'Diff (증감)']
diff_between_dept_ratio = df_compare.loc['between_department_ratio', 'Diff (증감)']
diff_density = df_compare.loc['density', 'Diff (증감)']
diff_avg_degree = df_compare.loc['average_degree', 'Diff (증감)']

if (diff_total_ties > 0 or
        diff_between_team_ratio > 0.05 or
        diff_between_dept_ratio > 0.05 or
        diff_density > 0.01 or
        diff_avg_degree > 0.5):
    final_verdict = "신규 프로젝트 이후 협업이 증가했을 가능성이 있습니다."
else:
    final_verdict = "신규 프로젝트 전후 협업 증가가 아주 뚜렷하지는 않습니다."

# ==========================================
# 7. 결과 화면 출력
# ==========================================
print("\n" + "=" * 50)
print("[3] 전체 요약 및 [4] 전후 비교 테이블")
print("=" * 50)
print(df_compare.round(4))

print("\n" + "=" * 50)
print("[5] 협업 증가 관련 핵심 비교 (Diff)")
print("=" * 50)
print(f" - 전체 협업량(Total Ties) 증감: {diff_total_ties:+.2f}")
print(f" - 팀 간 협업 비율 증감: {diff_between_team_ratio:+.4f}")
print(f" - 부서 간 협업 비율 증감: {diff_between_dept_ratio:+.4f}")
print(f" - 네트워크 밀도(Density) 증감: {diff_density:+.4f}")
print(f" - 평균 연결 정도(Avg Degree) 증감: {diff_avg_degree:+.4f}")

print(f"\n[최종 판정]\n>>> {final_verdict}")

# ==========================================
# 8. 엑셀 파일 하나에 다중 시트로 통합 저장
# ==========================================
output_excel_filename = "SNA_분석_결과_보고서.xlsx"
output_excel_path = os.path.join(base_dir, output_excel_filename)

print("\n" + "=" * 50)
print(f"[엑셀 통합 저장 시작] 경로: {output_excel_path}")
print("=" * 50)

# ExcelWriter를 사용하여 여러 시트 생성
with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
    df_compare.to_excel(writer, sheet_name='전후_비교_요약_지표')
    pre_team_matrix.to_excel(writer, sheet_name='Pre_팀별_협업매트릭스')
    post_team_matrix.to_excel(writer, sheet_name='Post_팀별_협업매트릭스')
    pre_dept_matrix.to_excel(writer, sheet_name='Pre_부서별_협업매트릭스')
    post_dept_matrix.to_excel(writer, sheet_name='Post_부서별_협업매트릭스')

print(f"✓ 성공: 5개의 분석 결과가 '{output_excel_filename}' 파일 내 개별 시트로 결합되었습니다.")
print(f"위치: {base_dir}")