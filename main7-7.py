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

# 저장 파일명 설정
OUT_SUMMARY = os.path.join(BASE_DIR, "2025Q2_사일로_요약.csv")
OUT_MATRIX = os.path.join(BASE_DIR, "2025Q2_팀별_연결_매트릭스.csv")
OUT_METRICS = os.path.join(BASE_DIR, "2025Q2_팀별_지표.csv")

print("데이터를 로드하고 사일로 분석을 시작합니다...\n")

# ==========================================
# --- 2. 데이터 로드 및 전처리 ---
# ==========================================
df_emp = pd.read_excel(EXCEL_PATH, sheet_name='employees')
df_edges_raw = pd.read_excel(EXCEL_PATH, sheet_name='edges')

# 직원 정보 매핑용 딕셔너리 (ID -> Team)
team_map = dict(zip(df_emp['employee_id'], df_emp['team']))
valid_ids = set(df_emp['employee_id'])

# 필터링: 2025Q2, communication, 자기 자신 제외, 유효한 직원만
df_filtered = df_edges_raw[
    (df_edges_raw['time_id'] == '2025Q2') &
    (df_edges_raw['tie_type'] == 'communication') &
    (df_edges_raw['source'] != df_edges_raw['target']) &
    (df_edges_raw['source'].isin(valid_ids)) &
    (df_edges_raw['target'].isin(valid_ids))
    ].copy()

# 팀 정보 매핑
df_filtered['source_team'] = df_filtered['source'].map(team_map)
df_filtered['target_team'] = df_filtered['target'].map(team_map)

# 팀 내(within) vs 팀 간(between) 구분
df_filtered['tie_category'] = np.where(df_filtered['source_team'] == df_filtered['target_team'], 'within', 'between')

# ==========================================
# --- 3. 통계용 Undirected Graph 생성 ---
# ==========================================
# source, target 정렬 후 통합 (Weight = interaction_count 합)
df_filtered['node_a'] = df_filtered[['source', 'target']].min(axis=1)
df_filtered['node_b'] = df_filtered[['source', 'target']].max(axis=1)
df_undirected = df_filtered.groupby(['node_a', 'node_b'])['interaction_count'].sum().reset_index()

G = nx.Graph()
# 노드 추가 및 팀 속성 부여
for _, row in df_emp.iterrows():
    G.add_node(row['employee_id'], team=row['team'])

for _, row in df_undirected.iterrows():
    G.add_edge(row['node_a'], row['node_b'], weight=row['interaction_count'])

# 고립 노드 제외 (계산용)
G_sub = G.subgraph([n for n, d in G.degree() if d > 0])

# ==========================================
# --- 4. 주요 지표 계산 ---
# ==========================================

# 1) 기초 수치
total_ties = len(df_undirected)
within_ties = len(df_undirected[df_filtered.groupby(['node_a', 'node_b'])['tie_category'].first().reset_index()[
                                    'tie_category'] == 'within'])
between_ties = total_ties - within_ties

within_ratio = within_ties / total_ties if total_ties > 0 else 0
between_ratio = 1 - within_ratio

# 2) Assortativity (팀 기준 유유상종 지수)
team_assortativity = nx.attribute_assortativity_coefficient(G, 'team')

# 3) Modularity (팀 그룹 기준 응집도)
# 팀별로 노드 그룹핑
teams = df_emp['team'].unique()
team_communities = [set(df_emp[df_emp['team'] == t]['employee_id']) for t in teams]
team_modularity = nx.community.modularity(G, team_communities, weight='weight')

# 4) 탐색적 Community Detection
detected_comms = list(nx.community.greedy_modularity_communities(G, weight='weight'))
detected_modularity = nx.community.modularity(G, detected_comms, weight='weight')
num_detected = len(detected_comms)

# 요약 테이블 생성
summary_data = {
    'Indicator': ['Total Ties', 'Within-Team Ties', 'Between-Team Ties', 'Within-Team Ratio',
                  'Between-Team Ratio', 'Team Assortativity', 'Team Modularity',
                  'Detected Community Modularity', 'Num of Detected Communities'],
    'Value': [total_ties, within_ties, between_ties, round(within_ratio, 4),
              round(between_ratio, 4), round(team_assortativity, 4), round(team_modularity, 4),
              round(detected_modularity, 4), num_detected]
}
summary_df = pd.DataFrame(summary_data)

# ==========================================
# --- 5. 팀별 세부 지표 및 매트릭스 ---
# ==========================================

# 팀별 지표 계산
team_stats = []
for t in teams:
    t_size = len(df_emp[df_emp['team'] == t])
    w_ties = len(df_filtered[(df_filtered['source_team'] == t) & (df_filtered['target_team'] == t)])
    b_out = len(df_filtered[(df_filtered['source_team'] == t) & (df_filtered['target_team'] != t)])
    b_in = len(df_filtered[(df_filtered['target_team'] == t) & (df_filtered['source_team'] != t)])
    b_total = b_out + b_in
    silo_index = w_ties / (w_ties + b_total) if (w_ties + b_total) > 0 else 0

    team_stats.append({
        'team': t, 'team_size': t_size, 'within_team_ties': w_ties,
        'between_team_out_ties': b_out, 'between_team_in_ties': b_in,
        'between_team_total_ties': b_total, 'silo_index': round(silo_index, 4)
    })
team_metrics_df = pd.DataFrame(team_stats)

# 팀-팀 연결 매트릭스 (Directed Raw Data 기준)
team_matrix = pd.pivot_table(df_filtered, values='interaction_count',
                             index='source_team', columns='target_team',
                             aggfunc='sum', fill_value=0)

# ==========================================
# --- 6. 결과 출력 및 판정 ---
# ==========================================
print("-" * 50)
print("1. [분석 기준] 시점: 2025Q2 | 유형: Communication | 대상: 전사 직원")
print("-" * 50)
print("2. [전체 요약]")
print(summary_df.to_string(index=False))
print("-" * 50)
print("3. [팀별 사일로 지표]")
print(team_metrics_df[['team', 'team_size', 'silo_index']].sort_values(by='silo_index', ascending=False).to_string(
    index=False))
print("-" * 50)
print("4. [팀-팀 연결 매트릭스 (Interaction Sum)]")
print(team_matrix)
print("-" * 50)

# 최종 판정
silo_risk = (within_ratio >= 0.7) or (team_assortativity >= 0.2) or (team_modularity >= 0.2)
judgment = "🚨 [판정] 팀 간 사일로 현상이 존재할 가능성이 높습니다." if silo_risk else "✅ [판정] 팀 간 협업 및 소통이 원활하게 분산되어 있습니다."

print("5. [해석 가이드]")
print(" - Within-Team Ratio: 0.7 이상이면 내부 소통이 지나치게 편중됨을 의미합니다.")
print(" - Team Assortativity: 1에 가까울수록 같은 팀끼리만 뭉치는 성향이 강합니다.")
print(" - Team Modularity: 0.2 이상이면 조직도상 팀이 통계적으로 고립된 군집을 형성함을 뜻합니다.")
print("\n6. " + judgment)

# 결과 저장
summary_df.to_csv(OUT_SUMMARY, index=False, encoding='utf-8-sig')
team_matrix.to_csv(OUT_MATRIX, encoding='utf-8-sig')
team_metrics_df.to_csv(OUT_METRICS, index=False, encoding='utf-8-sig')
print(f"\n✅ 분석 결과(CSV 3개) 저장 완료: {BASE_DIR}")