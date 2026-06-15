import pandas as pd
import numpy as np
import networkx as nx
from networkx.algorithms import community
from sklearn.metrics import normalized_mutual_info_score
import os

# ==========================================
# 1. 환경 설정 및 데이터 불러오기
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"
base_dir = os.path.dirname(file_path)

print("데이터를 불러오고 전처리를 진행합니다...")
employees = pd.read_excel(file_path, sheet_name='employees')
edges = pd.read_excel(file_path, sheet_name='edges')

# ==========================================
# 2. 데이터 전처리
# ==========================================
# 2-1. 통신 데이터 필터링 및 자기 자신 연결 제거
edges = edges[edges['tie_type'] == 'communication'].copy()
edges = edges[edges['source'] != edges['target']].copy()

# 2-2. employees 시트 기준 유효 직원 필터링
valid_employees = set(employees['employee_id'])
edges = edges[edges['source'].isin(valid_employees) & edges['target'].isin(valid_employees)].copy()

# 2-3. Undirected 기준으로 통합 (node 정렬)
edges['node1'] = np.where(edges['source'] < edges['target'], edges['source'], edges['target'])
edges['node2'] = np.where(edges['source'] < edges['target'], edges['target'], edges['source'])

# 2-4. 가중치(interaction_count) 합산
edges_agg = edges.groupby(['time_id', 'node1', 'node2']).agg(
    interaction_count=('interaction_count', 'sum')
).reset_index()

time_ids = sorted(edges_agg['time_id'].unique())

# ==========================================
# 3. 커뮤니티 탐지 (Greedy Modularity)
# ==========================================
summary_data = []
comm_dict = {}  # time_id 별 커뮤니티 노드셋 저장
node_to_comm = {}  # time_id 별 노드 소속 커뮤니티 ID 매핑
membership_data = []  # 시점별 소속 저장용 (엑셀 출력용)

for t in time_ids:
    df_t = edges_agg[edges_agg['time_id'] == t]

    G = nx.Graph()
    G.add_nodes_from(valid_employees)  # 전체 노드 베이스

    for _, row in df_t.iterrows():
        G.add_edge(row['node1'], row['node2'], weight=row['interaction_count'])

    # 연결선이 없는 고립 노드 제거 후 탐지
    G_active = G.subgraph([n for n, d in G.degree() if d > 0])

    if G_active.number_of_edges() > 0:
        # Greedy Modularity Communities 사용
        comms = list(community.greedy_modularity_communities(G_active, weight='weight'))
        comms = sorted(comms, key=len, reverse=True)  # 크기 순 정렬
        mod_score = community.modularity(G_active, comms, weight='weight')

        sizes = [len(c) for c in comms]
        comm_dict[t] = comms

        node_map = {}
        for cid, c_nodes in enumerate(comms):
            for node in c_nodes:
                node_map[node] = cid
                membership_data.append({'time_id': t, 'employee_id': node, 'community_id': cid})

        node_to_comm[t] = node_map

        summary_data.append({
            'time_id': t,
            'num_communities': len(comms),
            'largest_community_size': max(sizes),
            'average_community_size': np.mean(sizes),
            'community_sizes_desc': ", ".join(map(str, sizes)),
            'community_modularity': mod_score
        })
    else:
        comm_dict[t] = []
        node_to_comm[t] = {}

df_summary = pd.DataFrame(summary_data)
df_membership = pd.DataFrame(membership_data)

# ==========================================
# 4. 시점 간 커뮤니티 전이 요약 (Overlap 및 NMI)
# ==========================================
transition_data = []
overlap_data = []

for i in range(len(time_ids) - 1):
    t0, t1 = time_ids[i], time_ids[i + 1]
    comms0, comms1 = comm_dict.get(t0, []), comm_dict.get(t1, [])

    # 4-1. NMI 계산 (두 시점 모두 소속된 교집합 노드 기준)
    nodes0 = set(node_to_comm.get(t0, {}).keys())
    nodes1 = set(node_to_comm.get(t1, {}).keys())
    common_nodes = list(nodes0 & nodes1)

    if common_nodes:
        y_t0 = [node_to_comm[t0][n] for n in common_nodes]
        y_t1 = [node_to_comm[t1][n] for n in common_nodes]
        nmi = normalized_mutual_info_score(y_t0, y_t1)
    else:
        nmi = 0.0

    # 4-2. Jaccard Overlap 계산 및 판정 (유지, 분리, 통합)
    matches_from_prev = {idx: 0 for idx in range(len(comms0))}
    matches_to_next = {idx: 0 for idx in range(len(comms1))}

    for i_cid, c0 in enumerate(comms0):
        for j_cid, c1 in enumerate(comms1):
            intersection = len(c0 & c1)
            union = len(c0 | c1)
            jaccard = intersection / union if union > 0 else 0

            is_strong = jaccard >= 0.3
            if is_strong:
                matches_from_prev[i_cid] += 1
                matches_to_next[j_cid] += 1

            if intersection > 0:  # 겹침이 1명이라도 있으면 기록
                overlap_data.append({
                    'time_period': f"{t0} -> {t1}",
                    'prev_comm_id': i_cid,
                    'next_comm_id': j_cid,
                    'jaccard_overlap': round(jaccard, 4),
                    'is_strong_match': is_strong
                })

    # 전이 카운트
    maintained = sum(1 for v in matches_from_prev.values() if v == 1)
    split = sum(1 for v in matches_from_prev.values() if v >= 2)
    merged = sum(1 for v in matches_to_next.values() if v >= 2)

    transition_data.append({
        'time_period': f"{t0} -> {t1}",
        'NMI_score': round(nmi, 4),
        'maintained_communities': maintained,
        'split_communities': split,
        'merged_communities': merged
    })

df_transitions = pd.DataFrame(transition_data)
df_overlap = pd.DataFrame(overlap_data).sort_values(by=['time_period', 'jaccard_overlap'], ascending=[True, False])

# ==========================================
# 5. 최종 판정 로직
# ==========================================
if not df_transitions.empty:
    avg_nmi = df_transitions['NMI_score'].mean()
    total_split = df_transitions['split_communities'].sum()
    total_merged = df_transitions['merged_communities'].sum()

    signals = []
    if avg_nmi >= 0.6:
        signals.append("전반적 커뮤니티 구조 유지")
    if total_split >= 1:
        signals.append("일부 커뮤니티 분리 발생")
    if total_merged >= 1:
        signals.append("일부 커뮤니티 통합 발생")

    print("\n[중간 판정 신호 확인]")
    for s in signals:
        print(f" - {s}")

    if signals:
        final_verdict = "커뮤니티 구조는 시점에 따라 유지되면서도 일부 분리/통합이 발생한 것으로 보입니다."
    else:
        final_verdict = "커뮤니티 구조 변화가 아주 뚜렷하지는 않습니다."
else:
    final_verdict = "전이(시점 간 비교)를 수행할 데이터가 부족합니다."

# ==========================================
# 6. 결과 화면 출력 (Print)
# ==========================================
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

print("\n" + "=" * 50)
print("[1] 분석 기준")
print("=" * 50)
print("- 타겟 연결 유형: communication (Undirected 가중치 적용)")
print("- 커뮤니티 탐지: Greedy Modularity (networkx)")
print("- 유지/분리/통합 기준: Jaccard Overlap >= 0.3 (Strong Match)")

print("\n" + "=" * 50)
print("[2] 시점별 커뮤니티 요약")
print("=" * 50)
print(df_summary.round(4).to_string(index=False))

print("\n" + "=" * 50)
print("[3] 시점 간 커뮤니티 전이 요약")
print("=" * 50)
print(df_transitions.to_string(index=False) if not df_transitions.empty else "데이터 없음")

print("\n" + "=" * 50)
print("[4] 해석 가이드")
print("=" * 50)
print("- NMI Score: 1에 가까울수록 이전 시점과 다음 시점의 파벌(커뮤니티) 소속 구조가 거의 동일함을 의미합니다.")
print("- maintained: 이전 그룹 구성원이 다음 시점에도 그대로 뭉쳐서 하나의 그룹을 형성한 횟수입니다.")
print("- split: 하나의 끈끈했던 그룹이 다음 분기에는 2개 이상의 파벌로 쪼개진(분열된) 횟수입니다.")
print("- merged: 분리되어 있던 2개 이상의 그룹 구성원들이 다음 분기에 하나의 거대 그룹으로 융합된 횟수입니다.")

print("\n" + "=" * 50)
print("[5] 커뮤니티 소속 예시 상위 10행")
print("=" * 50)
print(df_membership.head(10).to_string(index=False))

print("\n" + "=" * 50)
print("[6] 커뮤니티 overlap 상세 예시 상위 10행")
print("=" * 50)
print(df_overlap.head(10).to_string(index=False))

print("\n" + "=" * 50)
print(f"[7] 최종 판정\n>>> {final_verdict}")
print("=" * 50)

# ==========================================
# 7. 엑셀 파일 저장 (다중 시트 통합)
# ==========================================
output_excel_path = os.path.join(base_dir, "SNA_커뮤니티_동학_분석.xlsx")

with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
    df_summary.to_excel(writer, sheet_name='시점별_커뮤니티_요약', index=False)
    if not df_transitions.empty:
        df_transitions.to_excel(writer, sheet_name='커뮤니티_전이_요약', index=False)
    df_membership.to_excel(writer, sheet_name='전체_멤버십_데이터', index=False)
    df_overlap.to_excel(writer, sheet_name='Overlap_상세_데이터', index=False)

print(f"\n✓ 성공: 분석 결과가 여러 시트로 구성된 하나의 엑셀 파일로 저장되었습니다.\n저장 경로: {output_excel_path}")