import pandas as pd
import networkx as nx
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. 파일 경로 설정 ---
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"
output_csv = os.path.join(os.path.dirname(file_path), "2025Q2_Broker_Analysis_Result.xlsx")

print("데이터를 불러오고 부서 간 네트워크 분석을 시작합니다...")

# ==========================================
# --- 2. 데이터 로드 및 부서 정보 매핑 ---
# ==========================================
df_emp = pd.read_excel(file_path, sheet_name='employees')
df_edges = pd.read_excel(file_path, sheet_name='edges')

# 부서 정보 딕셔너리 생성 (ID -> Dept)
dept_map = dict(zip(df_emp['employee_id'], df_emp['department']))

# 2025 Q2 필터링 및 자기 자신 제외
df_q2 = df_edges[(df_edges['time_id'] == '2025Q2') & (df_edges['source'] != df_edges['target'])].copy()

# source와 target에 부서 정보 매핑
df_q2['source_dept'] = df_q2['source'].map(dept_map)
df_q2['target_dept'] = df_q2['target'].map(dept_map)

# 부서 간 연결(Cross-Department) 정의
df_cross = df_q2[df_q2['source_dept'] != df_q2['target_dept']].copy()

# ==========================================
# --- 3. SNA 지표 계산 ---
# ==========================================

# (1) Betweenness Centrality (Undirected Graph 기준)
# 원자료가 Directed라도 요청에 따라 Undirected Edge로 통합하여 계산
G = nx.Graph()
for _, row in df_q2.iterrows():
    u, v, w = row['source'], row['target'], row['interaction_count']
    if G.has_edge(u, v):
        G[u][v]['weight'] += w
    else:
        G.add_edge(u, v, weight=w)

# 매개 중심성 계산 (weight를 고려하여 계산 가능하나, 보통 연결 구조 자체를 보기 위해 일반 BC 사용)
betweenness = nx.betweenness_centrality(G, normalized=True)
df_bt = pd.DataFrame(list(betweenness.items()), columns=['employee_id', 'betweenness_centrality'])

# (2) Cross-Dept 지표 계산 (부서 간 연결 데이터만 사용)
# 고유 상대방 수 (Unique Connections)
s_to_t = df_cross[['source', 'target']].rename(columns={'source': 'emp_id', 'target': 'partner'})
t_to_s = df_cross[['target', 'source']].rename(columns={'target': 'emp_id', 'source': 'partner'})
combined_cross = pd.concat([s_to_t, t_to_s])
unique_conn = combined_cross.groupby('emp_id')['partner'].nunique().rename('cross_dept_unique_connections')

# Out-degree & In-degree
out_degree = df_cross.groupby('source')['target'].nunique().rename('cross_dept_out_degree')
in_degree = df_cross.groupby('target')['source'].nunique().rename('cross_dept_in_degree')

# Interaction 총합
sent_int = df_cross.groupby('source')['interaction_count'].sum().rename('sent')
recv_int = df_cross.groupby('target')['interaction_count'].sum().rename('recv')

# ==========================================
# --- 4. 데이터 통합 및 결과 처리 ---
# ==========================================
# 지표 병합
metrics = pd.concat([unique_conn, out_degree, in_degree, sent_int, recv_int], axis=1).fillna(0)
metrics['cross_total_interaction'] = metrics['sent'] + metrics['recv']
metrics = metrics.drop(columns=['sent', 'recv'])
metrics.index.name = 'employee_id'

# 직원 정보와 병합
final_df = pd.merge(df_emp, df_bt, on='employee_id', how='left')
final_df = pd.merge(final_df, metrics, on='employee_id', how='left').fillna(0)

# 정렬: BC(내림) -> Unique(내림) -> Total Interaction(내림)
final_df = final_df.sort_values(
    by=['betweenness_centrality', 'cross_dept_unique_connections', 'cross_total_interaction'],
    ascending=False
).reset_index(drop=True)

# 순위 부여 및 상위 10명 추출
final_df.insert(0, 'rank', final_df.index + 1)
top_10_brokers = final_df.head(10)

# 콘솔 출력용 컬럼 선택
cols = ['rank', 'name', 'department', 'job_level', 'betweenness_centrality', 'cross_dept_unique_connections', 'cross_total_interaction']
print("\n" + "="*95)
print("🔍 2025 Q2 조직 내 핵심 브로커 (부서 간 연결 매개자) Top 10")
print("="*95)
print(top_10_brokers[cols].to_string(index=False))
print("="*95)

# 엑셀/CSV로 저장 (분석 결과 보존)
final_df.to_excel(output_csv, index=False)
print(f"\n✅ 분석 결과가 저장되었습니다: {output_csv}")