import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings

warnings.filterwarnings('ignore')

# --- 1. 파일 경로 및 설정 ---
EXCEL_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"

# 한글 폰트 설정 (Windows '맑은 고딕')
plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# --- 2. 데이터 로드 및 전처리 ---
print("데이터를 분석하고 있습니다...")

# 1) 시트별 데이터 읽기
df_emp = pd.read_excel(EXCEL_PATH, sheet_name='employees')
df_edges_raw = pd.read_excel(EXCEL_PATH, sheet_name='edges')

# 2) 조건 필터링: 2025Q2 시점 & 자기 자신 제외
df_edges = df_edges_raw[
    (df_edges_raw['time_id'] == '2025Q2') &
    (df_edges_raw['source'] != df_edges_raw['target'])
].copy()

# 3) Undirected 통합 (source, target 순서 정렬 후 합산)
df_edges['node_a'] = df_edges[['source', 'target']].min(axis=1)
df_edges['node_b'] = df_edges[['source', 'target']].max(axis=1)

df_undirected = df_edges.groupby(['node_a', 'node_b'])['interaction_count'].sum().reset_index()

# --- 3. 네트워크 그래프 생성 ---
G = nx.Graph()

# 노드 추가 (속성 포함)
for _, row in df_emp.iterrows():
    G.add_node(row['employee_id'],
               name=row['name'],
               department=row['department'],
               team=row['team'])

# 엣지 추가 (weight = interaction_count)
for _, row in df_undirected.iterrows():
    G.add_edge(row['node_a'], row['node_b'], weight=row['interaction_count'])

# 연결이 전혀 없는 고립 노드 제거
G.remove_nodes_from(list(nx.isolates(G)))

# --- 4. 시각화 변수 설정 ---
# 노드 크기: Degree(연결 수) 기반
degree_dict = dict(G.degree())
node_sizes = [v * 100 for v in degree_dict.values()]

# 노드 색상: 부서(Department) 기반
depts = sorted(df_emp['department'].unique())
color_map_list = plt.cm.get_cmap('Set3', len(depts))
dept_color_dict = {dept: color_map_list(i) for i, dept in enumerate(depts)}
node_colors = [dept_color_dict[G.nodes[n]['department']] for n in G.nodes()]

# 엣지 두께: interaction_count(weight) 기반
weights = [G[u][v]['weight'] * 0.5 for u, v in G.edges()]

# 라벨 표시: Degree 상위 15명 추출
top_15_nodes = sorted(degree_dict, key=degree_dict.get, reverse=True)[:15]
labels = {n: G.nodes[n]['name'] if n in top_15_nodes else '' for n in G.nodes()}

# --- 5. 그래프 그리기 ---
plt.figure(figsize=(15, 12))
pos = nx.spring_layout(G, k=0.5, seed=42) # 레이아웃 설정

# 노드 및 엣지 드로잉
nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors, alpha=0.9)
nx.draw_networkx_edges(G, pos, width=weights, edge_color='gray', alpha=0.3)
nx.draw_networkx_labels(G, pos, labels=labels, font_size=10, font_family='Malgun Gothic', font_weight='bold')

# 부서별 범례(Legend) 생성
legend_handles = [mpatches.Patch(color=dept_color_dict[dept], label=dept) for dept in depts]
plt.legend(handles=legend_handles, title="부서(Department)", loc='upper right', bbox_to_anchor=(1.2, 1))

# 제목 및 레이아웃 정리
plt.title("2025 Q2 조직 연결망 분석 (SNA)\n[조건: 모든 Tie Type 포함, Undirected]", fontsize=18, pad=20)
plt.axis('off')
plt.tight_layout()

print("✅ 네트워크 시각화 완료")
plt.show()