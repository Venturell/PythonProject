import pandas as pd
import networkx as nx
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. 파일 경로 설정 ---
# ==========================================
# 🚨 파일 확장자 오타(.xlsxx -> .xlsx)를 수정하여 적용했습니다.
EXCEL_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"
OUTPUT_CSV = os.path.join(os.path.dirname(EXCEL_PATH), "2025Q2_Advice_Informal_Leaders.csv")

print("데이터를 불러오고 Advice 네트워크 분석을 시작합니다...\n")

# ==========================================
# --- 2. 데이터 로드 및 전처리 ---
# ==========================================
df_emp = pd.read_excel(EXCEL_PATH, sheet_name='employees')
df_edges = pd.read_excel(EXCEL_PATH, sheet_name='edges')

# 1) 조건 필터링: 2025Q2, Advice 네트워크, 자기 자신 제외
df_filtered = df_edges[
    (df_edges['time_id'] == '2025Q2') &
    (df_edges['tie_type'] == 'advice') &
    (df_edges['source'] != df_edges['target'])
].copy()

# 2) Undirected 통합: source와 target을 알파벳/숫자 순으로 정렬하여 양방향 통합
df_filtered['node_a'] = df_filtered[['source', 'target']].min(axis=1)
df_filtered['node_b'] = df_filtered[['source', 'target']].max(axis=1)

# interaction_count(weight) 합산
df_undirected = df_filtered.groupby(['node_a', 'node_b'])['interaction_count'].sum().reset_index()

# ==========================================
# --- 3. 네트워크 생성 및 지표 계산 ---
# ==========================================
G = nx.Graph()

# 엣지 및 가중치 추가
for _, row in df_undirected.iterrows():
    G.add_edge(row['node_a'], row['node_b'], weight=row['interaction_count'])

# 지표 1 & 2: Degree 및 Weighted Degree 계산
degree_dict = dict(G.degree())
weighted_degree_dict = dict(G.degree(weight='weight'))

# 지표 3: 위세 중심성 (Eigenvector Centrality) 계산
try:
    # 기본 알고리즘 (최대 1000번 반복으로 여유있게 설정)
    ev_centrality = nx.eigenvector_centrality(G, weight='weight', max_iter=1000)
except nx.PowerIterationFailedConvergence:
    print("⚠️ 기본 알고리즘 수렴에 실패했습니다. Numpy 기반 알고리즘으로 재시도합니다...")
    ev_centrality = nx.eigenvector_centrality_numpy(G, weight='weight')

# 계산된 지표들을 데이터프레임으로 변환
metrics_df = pd.DataFrame({
    'employee_id': list(G.nodes()),
    'eigenvector_centrality': [ev_centrality.get(n, 0) for n in G.nodes()],
    'degree': [degree_dict.get(n, 0) for n in G.nodes()],
    'weighted_degree': [weighted_degree_dict.get(n, 0) for n in G.nodes()]
})

# ==========================================
# --- 4. 데이터 통합 및 비공식 리더 추출 ---
# ==========================================
# 필요한 직원 정보 병합
emp_cols = ['employee_id', 'name', 'department', 'team', 'job_level', 'is_manager']
merged_df = pd.merge(df_emp[emp_cols], metrics_df, on='employee_id', how='inner')

# 비공식 리더 조건: 관리자가 아닌 직원 (is_manager == 0)
informal_leaders = merged_df[merged_df['is_manager'] == 0].copy()

# 정렬: EV (내림차순) -> Degree (내림차순) -> Weighted Degree (내림차순)
informal_leaders = informal_leaders.sort_values(
    by=['eigenvector_centrality', 'degree', 'weighted_degree'],
    ascending=[False, False, False]
).reset_index(drop=True)

# 순위(Rank) 컬럼 추가
informal_leaders.insert(0, 'rank', informal_leaders.index + 1)

# 상위 10명 추출
top_10_leaders = informal_leaders.head(10)

# ==========================================
# --- 5. 결과 출력 및 저장 ---
# ==========================================
print("=" * 100)
print("🌟 2025 Q2 숨겨진 비공식 리더 Top 10 (Advice Network 기준)")
print("=" * 100)

# 콘솔 출력을 위해 주요 컬럼만 선택
display_cols = ['rank', 'name', 'department', 'job_level', 'eigenvector_centrality', 'degree', 'weighted_degree']
print(top_10_leaders[display_cols].to_string(index=False))
print("=" * 100)

# 전체 결과 CSV 저장 (한글 깨짐 방지 utf-8-sig)
informal_leaders.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
print(f"\n✅ 비공식 리더 전체 명단이 CSV로 저장되었습니다.\n저장 경로: {OUTPUT_CSV}")