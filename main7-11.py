import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. 파일 경로 및 분석 설정 ---
# ==========================================
EXCEL_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"
TARGET_EMPLOYEE_ID = "E023"  # 분석 대상 직원 ID 지정

# 한글 폰트 설정 (Windows 환경)
plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

print(f"데이터를 로드하고 '{TARGET_EMPLOYEE_ID}' 직원의 시계열 변화 분석을 시작합니다...\n")

# ==========================================
# --- 2. 데이터 로드 및 전처리 ---
# ==========================================
# 시트명 소문자 처리 (요청에는 Employees로 되어 있으나 통일성을 위해)
try:
    df_emp = pd.read_excel(EXCEL_PATH, sheet_name='employees')
except ValueError:
    df_emp = pd.read_excel(EXCEL_PATH, sheet_name='Employees')

df_edges_raw = pd.read_excel(EXCEL_PATH, sheet_name='edges')

valid_ids = set(df_emp['employee_id'])

# 타겟 직원이 존재하는지 검증
if TARGET_EMPLOYEE_ID not in valid_ids:
    print(f"❌ [오류] '{TARGET_EMPLOYEE_ID}' 직원이 employees 시트에 존재하지 않습니다.")
    exit()

target_info = df_emp[df_emp['employee_id'] == TARGET_EMPLOYEE_ID].iloc[0]

# 필터링: communication, 자기 자신 제외, 유효 직원
df_filtered = df_edges_raw[
    (df_edges_raw['tie_type'] == 'communication') &
    (df_edges_raw['source'] != df_edges_raw['target']) &
    (df_edges_raw['source'].isin(valid_ids)) &
    (df_edges_raw['target'].isin(valid_ids))
    ].copy()

# 시점(time_id) 추출 및 정렬
time_ids = sorted(df_filtered['time_id'].unique())

# ==========================================
# --- 3. 시점별 지표 계산 ---
# ==========================================
metrics_list = []

for t in time_ids:
    df_t = df_filtered[df_filtered['time_id'] == t].copy()

    # Undirected 변환
    df_t['node_a'] = df_t[['source', 'target']].min(axis=1)
    df_t['node_b'] = df_t[['source', 'target']].max(axis=1)
    df_undirected = df_t.groupby(['node_a', 'node_b'])['interaction_count'].sum().reset_index()

    # Graph 생성
    G = nx.Graph()
    G.add_nodes_from(valid_ids)  # 전체 유효 직원 추가
    for _, row in df_undirected.iterrows():
        G.add_edge(row['node_a'], row['node_b'], weight=row['interaction_count'])

    # 고립 노드를 제외한 Active 그래프 (네트워크 전체 지표용)
    G_active = G.subgraph([n for n, d in G.degree() if d > 0])

    # 중심성 계산
    deg_dict = dict(G.degree())
    w_deg_dict = dict(G.degree(weight='weight'))
    deg_cent = nx.degree_centrality(G)
    btwn_cent = nx.betweenness_centrality(G, weight='weight', normalized=True)

    try:
        eigen_cent = nx.eigenvector_centrality(G, weight='weight', max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        eigen_cent = nx.eigenvector_centrality_numpy(G, weight='weight')

    # 타겟 직원 데이터 추출
    metrics_list.append({
        'time_id': t,
        'degree': deg_dict.get(TARGET_EMPLOYEE_ID, 0),
        'weighted_degree': w_deg_dict.get(TARGET_EMPLOYEE_ID, 0),
        'degree_centrality': round(deg_cent.get(TARGET_EMPLOYEE_ID, 0), 4),
        'betweenness_centrality': round(btwn_cent.get(TARGET_EMPLOYEE_ID, 0), 4),
        'eigenvector_centrality': round(eigen_cent.get(TARGET_EMPLOYEE_ID, 0), 4),
        'number_of_nodes': G_active.number_of_nodes(),
        'number_of_edges': G_active.number_of_edges()
    })

df_metrics = pd.DataFrame(metrics_list)

# 시점별 변화량(Delta) 계산
for col in ['degree', 'weighted_degree', 'degree_centrality', 'betweenness_centrality', 'eigenvector_centrality']:
    df_metrics[f'{col}_change'] = df_metrics[col].diff().fillna(0).round(4)

# ==========================================
# --- 4. 콘솔 출력 및 판정 ---
# ==========================================
print("=" * 80)
print("1. [분석 기준]")
print(f" - 분석 대상 네트워크: Communication (Undirected 변환, 자기자신 제외)")
print(f" - 시점 목록: {', '.join(time_ids)}")
print("-" * 80)

print("2. [분석 대상 직원 정보]")
print(f" - ID: {target_info['employee_id']}")
print(f" - 이름: {target_info['name']}")
print(f" - 부서/팀: {target_info['department']} / {target_info['team']}")
print(f" - 직급(매니저 여부): {target_info['job_level']} (Manager: {bool(target_info['is_manager'])})")
print("-" * 80)

print("3. [시점별 Centrality 변화표]")
# 보기 편하게 주요 컬럼만 출력
display_cols = ['time_id', 'degree', 'weighted_degree', 'degree_centrality', 'betweenness_centrality',
                'eigenvector_centrality']
print(df_metrics[display_cols].to_string(index=False))

print("\n[전기 대비 변화량(Delta)]")
change_cols = ['time_id'] + [c for c in df_metrics.columns if '_change' in c]
print(df_metrics[change_cols].to_string(index=False))
print("-" * 80)

print("4. [해석 가이드]")
print(" - Degree: 직접 소통하는 동료의 수 (마당발 여부)")
print(" - Betweenness: 부서나 그룹 간 소통을 매개하는 정도 (브로커 여부)")
print(" - Eigenvector: 핵심 인물(경영진, 타 리더 등)과 연결된 정도 (실세 여부)")
print(" ※ Rising Star는 단순히 Degree만 늘어나는 것이 아니라 Betweenness와 Eigenvector가 함께 증가하는 패턴을 보입니다.")
print("-" * 80)

# 최종 판정 로직 (첫 시점 vs 마지막 시점)
first_metrics = df_metrics.iloc[0]
last_metrics = df_metrics.iloc[-1]

diff_degree = last_metrics['degree'] - first_metrics['degree']
diff_betweenness = last_metrics['betweenness_centrality'] - first_metrics['betweenness_centrality']
diff_eigenvector = last_metrics['eigenvector_centrality'] - first_metrics['eigenvector_centrality']

is_rising = (
        (diff_degree > 0) or
        (diff_betweenness > 0.01) or
        (diff_eigenvector > 0.01)
)

print("5. [최종 판정]")
if is_rising:
    print(
        f" 🌟 [판결]: {target_info['employee_id']} ({target_info['name']}) 직원의 중심성은 전반적으로 증가했을 가능성이 있습니다. (Rising Star 후보)")
else:
    print(f" ⚖️ [판결]: {target_info['employee_id']} ({target_info['name']}) 직원의 중심성 변화가 아주 뚜렷하지는 않습니다.")
print("=" * 80)

# ==========================================
# --- 5. 시각화 (선 그래프) ---
# ==========================================
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 그래프 1: Degree 및 Weighted Degree
axes[0].plot(df_metrics['time_id'], df_metrics['degree'], marker='o', label='Degree', color='blue', linewidth=2)
axes[0].set_title(f"[{target_info['name']}] 연결 수 (Degree) 변화", fontsize=13)
axes[0].set_xlabel("Time ID")
axes[0].set_ylabel("Count")
axes[0].grid(True, linestyle='--', alpha=0.6)
axes[0].legend()

# 그래프 2: Centrality 지표
axes[1].plot(df_metrics['time_id'], df_metrics['degree_centrality'], marker='s', label='Degree Centrality',
             linestyle='--')
axes[1].plot(df_metrics['time_id'], df_metrics['betweenness_centrality'], marker='^', label='Betweenness Centrality',
             linewidth=2)
axes[1].plot(df_metrics['time_id'], df_metrics['eigenvector_centrality'], marker='D', label='Eigenvector Centrality',
             linewidth=2)
axes[1].set_title(f"[{target_info['name']}] 핵심 중심성(Centrality) 지표 변화", fontsize=13)
axes[1].set_xlabel("Time ID")
axes[1].set_ylabel("Score (0~1)")
axes[1].grid(True, linestyle='--', alpha=0.6)
axes[1].legend()

plt.tight_layout()
plt.show()