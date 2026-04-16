import pandas as pd
import networkx as nx
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. 파일 경로 설정 ---
# ==========================================
EXCEL_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"
BASE_DIR = os.path.dirname(EXCEL_PATH)

OUTPUT_ALL = os.path.join(BASE_DIR, "2025Q2_Collaboration_All.csv")
OUTPUT_ISOLATED = os.path.join(BASE_DIR, "2025Q2_Collaboration_Isolated.csv")
OUTPUT_LOW_CONN = os.path.join(BASE_DIR, "2025Q2_Collaboration_LowConnection.csv")

print("데이터를 불러오고 고립 직원(Isolation) 분석을 시작합니다...\n")

# ==========================================
# --- 2. 데이터 로드 및 전처리 ---
# ==========================================
df_emp = pd.read_excel(EXCEL_PATH, sheet_name='employees')
df_edges = pd.read_excel(EXCEL_PATH, sheet_name='edges')

# employees 시트에 있는 유효한 직원 ID 목록 추출
valid_emp_ids = set(df_emp['employee_id'])

# 필터링 조건 적용
df_filtered = df_edges[
    (df_edges['time_id'] == '2025Q2') &
    (df_edges['tie_type'] == 'collaboration') &
    (df_edges['source'] != df_edges['target']) &
    (df_edges['source'].isin(valid_emp_ids)) &
    (df_edges['target'].isin(valid_emp_ids))
].copy()

# ==========================================
# --- 3. Directed 지표 계산 (원자료 기준) ---
# ==========================================
out_degree = df_filtered.groupby('source')['target'].nunique().rename('out_degree')
in_degree = df_filtered.groupby('target')['source'].nunique().rename('in_degree')
sent_int = df_filtered.groupby('source')['interaction_count'].sum().rename('sent_interaction')
recv_int = df_filtered.groupby('target')['interaction_count'].sum().rename('received_interaction')

# ==========================================
# --- 4. Undirected 네트워크 생성 및 지표 계산 ---
# ==========================================
# 양방향 통합
df_filtered['node_a'] = df_filtered[['source', 'target']].min(axis=1)
df_filtered['node_b'] = df_filtered[['source', 'target']].max(axis=1)
df_undirected = df_filtered.groupby(['node_a', 'node_b'])['interaction_count'].sum().reset_index()

# NetworkX 그래프 생성
G = nx.Graph()
# 🚨 핵심: 엣지가 하나도 없는 고립 직원을 찾기 위해 전체 직원을 노드로 먼저 추가
G.add_nodes_from(df_emp['employee_id'])

for _, row in df_undirected.iterrows():
    G.add_edge(row['node_a'], row['node_b'], weight=row['interaction_count'])

degree_dict = dict(G.degree())
weighted_degree_dict = dict(G.degree(weight='weight'))

# ==========================================
# --- 5. 데이터 병합 및 파생 변수 생성 ---
# ==========================================
metrics_df = pd.DataFrame({
    'employee_id': list(G.nodes()),
    'degree': [degree_dict.get(n, 0) for n in G.nodes()],
    'weighted_degree': [weighted_degree_dict.get(n, 0) for n in G.nodes()]
}).set_index('employee_id')

# 모든 지표 Join
metrics_combined = pd.concat([metrics_df, out_degree, in_degree, sent_int, recv_int], axis=1).fillna(0)
metrics_combined['total_interaction'] = metrics_combined['sent_interaction'] + metrics_combined['received_interaction']
metrics_combined = metrics_combined.drop(columns=['sent_interaction', 'received_interaction']).reset_index()
metrics_combined = metrics_combined.rename(columns={'index': 'employee_id'})

# 고립/저연결 상태 정의
metrics_combined['is_isolated'] = (metrics_combined['degree'] == 0).astype(int)
metrics_combined['is_low_connection'] = (metrics_combined['degree'] <= 2).astype(int)

def assign_network_status(d):
    if d == 0: return "isolated"
    elif d <= 2: return "low_connection"
    else: return "connected"

metrics_combined['network_status'] = metrics_combined['degree'].apply(assign_network_status)

# 정수형 변환
for col in ['degree', 'weighted_degree', 'out_degree', 'in_degree', 'total_interaction']:
    metrics_combined[col] = metrics_combined[col].astype(int)

# 직원 기본 정보와 최종 병합
emp_cols = ['employee_id', 'name', 'department', 'team', 'job_level', 'is_manager']
final_df = pd.merge(df_emp[emp_cols], metrics_combined, on='employee_id', how='left')

# 정렬: degree 오름차순, total_interaction 오름차순
final_df = final_df.sort_values(by=['degree', 'total_interaction'], ascending=[True, True]).reset_index(drop=True)

# ==========================================
# --- 6. 그룹별 데이터 추출 및 파일 저장 ---
# ==========================================
# 1) 전체 결과
final_df.to_csv(OUTPUT_ALL, index=False, encoding='utf-8-sig')

# 2) 완전 고립 직원
isolated_df = final_df[final_df['is_isolated'] == 1].reset_index(drop=True)
isolated_df.to_csv(OUTPUT_ISOLATED, index=False, encoding='utf-8-sig')

# 3) 저연결 직원 (degree <= 2)
low_conn_df = final_df[final_df['is_low_connection'] == 1].copy().reset_index(drop=True)
low_conn_df.insert(0, 'rank_low_to_high', low_conn_df.index + 1) # 정렬된 상태에서 랭크 추가
low_conn_df.to_csv(OUTPUT_LOW_CONN, index=False, encoding='utf-8-sig')

# ==========================================
# --- 7. 결과 콘솔 출력 (각 집단별 Top 10) ---
# ==========================================
display_cols = ['name', 'department', 'job_level', 'degree', 'total_interaction', 'network_status']

print("=" * 80)
print("📊 [1] 전체 직원 중 고립 위험 순위 (Top 10)")
print("=" * 80)
print(final_df.head(10)[display_cols].to_string(index=False))

print("\n" + "=" * 80)
print("⚠️ [2] 완전 고립 직원 (협업 없음, Top 10)")
print("=" * 80)
if len(isolated_df) > 0:
    print(isolated_df.head(10)[display_cols].to_string(index=False))
else:
    print("완전 고립 직원이 없습니다.")

print("\n" + "=" * 80)
print("📉 [3] 저연결 직원 (협업 2명 이하, Top 10)")
print("=" * 80)
if len(low_conn_df) > 0:
    print(low_conn_df.head(10)[['rank_low_to_high'] + display_cols].to_string(index=False))
else:
    print("저연결 직원이 없습니다.")
print("=" * 80)

print(f"\n✅ 3개의 분석 결과 파일이 모두 저장되었습니다.\n폴더 위치: {BASE_DIR}")