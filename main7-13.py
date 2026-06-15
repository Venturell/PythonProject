import pandas as pd
import numpy as np
import networkx as nx
from itertools import combinations
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import os

# ==========================================
# 1. 환경 설정 및 데이터 불러오기
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"
base_dir = os.path.dirname(file_path)

print("데이터 불러오기 및 전처리 중...")
employees = pd.read_excel(file_path, sheet_name='employees')
edges = pd.read_excel(file_path, sheet_name='edges')

# ==========================================
# 2. 데이터 전처리
# ==========================================
# tie_type 필터링 및 자기 자신 연결 제거
edges = edges[edges['tie_type'] == 'collaboration'].copy()
edges = edges[edges['source'] != edges['target']].copy()

# 유효한 직원 필터링
valid_employees = set(employees['employee_id'])
edges = edges[edges['source'].isin(valid_employees) & edges['target'].isin(valid_employees)].copy()

# Undirected Dyad 기준 통합 (정렬)
edges['node_u'] = np.where(edges['source'] < edges['target'], edges['source'], edges['target'])
edges['node_v'] = np.where(edges['source'] < edges['target'], edges['target'], edges['source'])

# time_id 별 가중치(interaction_count) 합산
edges_agg = edges.groupby(['time_id', 'node_u', 'node_v'])['interaction_count'].sum().reset_index()

time_ids = sorted(edges_agg['time_id'].unique())
all_dyads = list(combinations(sorted(list(valid_employees)), 2))

# 직원 정보 딕셔너리 구성 (빠른 검색용)
emp_dict = employees.set_index('employee_id').to_dict('index')


# ==========================================
# 3. Feature 생성 함수 정의
# ==========================================
def safe_metric(metric_func, G, u, v):
    try:
        return list(metric_func(G, [(u, v)]))[0][2]
    except:
        return 0.0


def build_features(t, G_t, G_next=None, is_train=True):
    data = []

    # 시간 t의 엣지 정보를 딕셔너리로 변환하여 빠른 검색 지원
    edge_weights = nx.get_edge_attributes(G_t, 'weight')

    for u, v in all_dyads:
        u_info, v_info = emp_dict[u], emp_dict[v]

        # 1. 노드 속성 Features
        same_team = 1 if u_info['team'] == v_info['team'] else 0
        same_department = 1 if u_info['department'] == v_info['department'] else 0
        job_level_gap = abs(u_info['job_level'] - v_info['job_level'])
        both_manager = 1 if u_info['is_manager'] == 1 and v_info['is_manager'] == 1 else 0
        either_manager = 1 if u_info['is_manager'] == 1 or v_info['is_manager'] == 1 else 0

        # 2. 네트워크 위상 Features
        degree_u = G_t.degree(u)
        degree_v = G_t.degree(v)
        degree_sum = degree_u + degree_v
        degree_diff = abs(degree_u - degree_v)
        common_neighbors = len(list(nx.common_neighbors(G_t, u, v)))

        jaccard = safe_metric(nx.jaccard_coefficient, G_t, u, v)
        adamic_adar = safe_metric(nx.adamic_adar_index, G_t, u, v)
        preferential_attachment = safe_metric(nx.preferential_attachment, G_t, u, v)

        # 3. 과거 상호작용 Features
        previous_tie = 1 if G_t.has_edge(u, v) else 0
        previous_edge_weight = edge_weights.get((u, v), edge_weights.get((v, u), 0))

        # 행 데이터 생성
        row = {
            'time_id': t, 'node_u': u, 'node_v': v,
            'same_team': same_team, 'same_department': same_department,
            'job_level_gap': job_level_gap, 'both_manager': both_manager, 'either_manager': either_manager,
            'degree_u': degree_u, 'degree_v': degree_v, 'degree_sum': degree_sum, 'degree_diff': degree_diff,
            'common_neighbors': common_neighbors, 'jaccard': jaccard, 'adamic_adar': adamic_adar,
            'preferential_attachment': preferential_attachment, 'previous_tie': previous_tie,
            'previous_edge_weight': previous_edge_weight
        }

        # 학습 데이터일 경우 Target 변수(y) 추가
        if is_train and G_next is not None:
            row['y_next_tie'] = 1 if G_next.has_edge(u, v) else 0

        data.append(row)
    return pd.DataFrame(data)


# 시점별 그래프 객체 생성 헬퍼
def get_graph_for_time(t_id):
    G = nx.Graph()
    G.add_nodes_from(valid_employees)
    df_t = edges_agg[edges_agg['time_id'] == t_id]
    for _, row in df_t.iterrows():
        G.add_edge(row['node_u'], row['node_v'], weight=row['interaction_count'])
    return G


# ==========================================
# 4. 학습 데이터셋(Train Data) 구축
# ==========================================
print("학습 데이터셋(Feature)을 생성하는 중입니다...")
train_frames = []
for i in range(len(time_ids) - 1):
    t_current = time_ids[i]
    t_next = time_ids[i + 1]

    G_current = get_graph_for_time(t_current)
    G_next = get_graph_for_time(t_next)

    df_features = build_features(t_current, G_current, G_next=G_next, is_train=True)
    train_frames.append(df_features)

train_df = pd.concat(train_frames, ignore_index=True)

# 피처 리스트 정리
feature_cols = [
    'same_team', 'same_department', 'job_level_gap', 'both_manager', 'either_manager',
    'degree_u', 'degree_v', 'degree_sum', 'degree_diff', 'common_neighbors',
    'jaccard', 'adamic_adar', 'preferential_attachment', 'previous_tie', 'previous_edge_weight'
]

X_train = train_df[feature_cols]
y_train = train_df['y_next_tie']

# ==========================================
# 5. 로지스틱 회귀 모델 학습
# ==========================================
print("로지스틱 회귀 모델 학습 중...")
model = LogisticRegression(max_iter=2000, random_state=42)
model.fit(X_train, y_train)

# 학습 성능(AUC) 계산
train_pred_prob = model.predict_proba(X_train)[:, 1]
train_auc = roc_auc_score(y_train, train_pred_prob)

# ==========================================
# 6. 예측 (마지막 시점 T 기준 T+1 예측)
# ==========================================
last_t = time_ids[-1]
G_last = get_graph_for_time(last_t)

print(f"마지막 관측 시점({last_t}) 기준으로 다음 분기 예측 중...")
test_df = build_features(last_t, G_last, is_train=False)
X_test = test_df[feature_cols]

# 예측 확률 계산
test_df['predicted_probability'] = model.predict_proba(X_test)[:, 1]

# 기존에 연결이 없는(새로운 협업) 데이터만 필터링 및 정렬
pred_new_only = test_df[test_df['previous_tie'] == 0].copy()
pred_new_only = pred_new_only.sort_values(by='predicted_probability', ascending=False)


# 직원 매핑 정보 추가
def map_emp_info(df):
    df['source_name'] = df['node_u'].apply(lambda x: emp_dict[x]['name'])
    df['source_department'] = df['node_u'].apply(lambda x: emp_dict[x]['department'])
    df['source_team'] = df['node_u'].apply(lambda x: emp_dict[x]['team'])

    df['target_name'] = df['node_v'].apply(lambda x: emp_dict[x]['name'])
    df['target_department'] = df['node_v'].apply(lambda x: emp_dict[x]['department'])
    df['target_team'] = df['node_v'].apply(lambda x: emp_dict[x]['team'])
    return df


pred_new_only = map_emp_info(pred_new_only)

# 출력용 열 정리
output_cols = [
    'node_u', 'source_name', 'source_department', 'source_team',
    'node_v', 'target_name', 'target_department', 'target_team',
    'predicted_probability', 'same_team', 'same_department', 'job_level_gap',
    'common_neighbors', 'jaccard', 'adamic_adar', 'preferential_attachment'
]
final_output = pred_new_only[output_cols]

# ==========================================
# 7. 결과 출력
# ==========================================
print("\n" + "=" * 60)
print("[1] 분석 기준")
print("=" * 60)
print("- 타겟 연결 유형: collaboration (Undirected)")
print("- 모델링 기법: Logistic Regression (Link Prediction)")
print(f"- 학습 기간 (t -> t+1): {time_ids[:-1]} -> {time_ids[1:]}")
print(f"- 예측 대상: {last_t} 시점 정보를 기반으로 한 다음 분기 신규 협업 확률")

print("\n" + "=" * 60)
print("[2] 학습 데이터 요약")
print("=" * 60)
print(f"- 학습에 사용된 총 Dyad(쌍) 수: {len(train_df):,} 건")
print(f"- 실제 협업이 발생한(Target=1) 비율: {y_train.mean():.2%}")
print(f"- 모델 Train ROC AUC Score: {train_auc:.4f}")

print("\n" + "=" * 60)
print("[3] 모델 계수 (주요 Feature 중요도 방향성)")
print("=" * 60)
coef_df = pd.DataFrame({'Feature': feature_cols, 'Coefficient': model.coef_[0]})
coef_df = coef_df.sort_values(by='Coefficient', ascending=False)
print(coef_df.round(4).to_string(index=False))

print("\n" + "=" * 60)
print("[4] 다음 분기 협업 가능성 상위 10개 Dyad (기존 협업 없음)")
print("=" * 60)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
print(final_output.head(10).round(4).to_string(index=False))

print("\n" + "=" * 60)
print("[5] 해석 가이드")
print("=" * 60)
print("- Predicted Probability: 1에 가까울수록 다음 분기에 두 사람이 새롭게 협업할 확률이 높음을 의미합니다.")
print("- Coefficient(양수): 해당 지표가 높을수록(예: 공통 지인이 많을수록) 협업 발생 확률을 크게 높입니다.")
print("- Coefficient(음수): 해당 지표가 높을수록(예: 직급 격차가 클수록) 협업 발생 확률을 낮춥니다.")

print("\n" + "=" * 60)
print("[6] 최종 판정")
print("=" * 60)

if not final_output.empty:
    top1 = final_output.iloc[0]
    u_id, u_name = top1['node_u'], top1['source_name']
    v_id, v_name = top1['node_v'], top1['target_name']
    prob = top1['predicted_probability']
    s_team = "O" if top1['same_team'] == 1 else "X"
    s_dept = "O" if top1['same_department'] == 1 else "X"
    c_neigh = top1['common_neighbors']

    print(f">>> 다음 분기에 새롭게 협업할 가능성이 높은 직원 쌍 후보를 도출했습니다.")
    print(f" - 1위 후보: {u_id}({u_name}) - {v_id}({v_name})")
    print(f" - 예측 확률: {prob:.2%}")
    print(f" - 세부 조건: 같은 팀({s_team}), 같은 부서({s_dept}), 공통 협업자 수({c_neigh}명)")
else:
    print(">>> 조건을 만족하는 신규 협업 예측 후보가 없습니다.")
print("=" * 60)

# ==========================================
# 8. 엑셀 파일 저장
# ==========================================
output_path = os.path.join(base_dir, "SNA_신규협업_예측결과.xlsx")
final_output.to_excel(output_path, index=False, engine='openpyxl')
print(f"\n✓ 예측 결과가 다음 경로에 저장되었습니다.\n{output_path}")