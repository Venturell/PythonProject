import pandas as pd
import numpy as np
import networkx as nx
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

# 직원 정보 딕셔너리 구성
emp_dict = employees.set_index('employee_id').to_dict('index')
valid_employees = sorted(list(emp_dict.keys()))

# ==========================================
# 2. 데이터 전처리
# ==========================================
edges = edges[edges['tie_type'] == 'communication'].copy()
edges = edges[edges['source'] != edges['target']].copy()
edges = edges[edges['source'].isin(valid_employees) & edges['target'].isin(valid_employees)].copy()

# Directed Graph용 데이터 (out_degree, in_degree 계산용)
edges_dir = edges.groupby(['time_id', 'source', 'target'])['interaction_count'].sum().reset_index()

# Undirected Graph용 데이터 (중심성, 일반 degree 계산용)
edges['node_u'] = np.where(edges['source'] < edges['target'], edges['source'], edges['target'])
edges['node_v'] = np.where(edges['source'] < edges['target'], edges['target'], edges['source'])
edges_undir = edges.groupby(['time_id', 'node_u', 'node_v'])['interaction_count'].sum().reset_index()

time_ids = sorted(edges['time_id'].unique())

# ==========================================
# 3. Feature 생성 (시점별/직원별)
# ==========================================
print("시점별 직원 Feature 및 타겟 변수 계산 중...")
feature_data = []

for t in time_ids:
    df_dir = edges_dir[edges_dir['time_id'] == t]
    df_undir = edges_undir[edges_undir['time_id'] == t]

    # 그래프 객체 생성
    G_d = nx.DiGraph()
    G_d.add_nodes_from(valid_employees)
    for _, row in df_dir.iterrows():
        G_d.add_edge(row['source'], row['target'], weight=row['interaction_count'])

    G_u = nx.Graph()
    G_u.add_nodes_from(valid_employees)
    for _, row in df_undir.iterrows():
        G_u.add_edge(row['node_u'], row['node_v'], weight=row['interaction_count'])

    # 중심성 지표 계산 (Undirected 기준)
    deg_cent = nx.degree_centrality(G_u)
    bet_cent = nx.betweenness_centrality(G_u, weight=None)
    try:
        eig_cent = nx.eigenvector_centrality(G_u, weight='weight', max_iter=1000, tol=1e-03)
    except nx.PowerIterationFailedConvergence:
        eig_cent = {n: 0 for n in valid_employees}

    for emp in valid_employees:
        info = emp_dict[emp]

        # 1) ~ 2) 직원 속성
        job_level = info['job_level']
        is_manager = info['is_manager']

        # 3) ~ 7) 기본 중심성 지표
        degree = G_u.degree(emp)
        weighted_degree = G_u.degree(emp, weight='weight')
        d_cent = deg_cent[emp]
        b_cent = bet_cent[emp]
        e_cent = eig_cent[emp]

        # 8) ~ 9) 방향성 지표
        out_degree = G_d.out_degree(emp)
        in_degree = G_d.in_degree(emp)

        # 10) ~ 13) Cross 특성 지표
        cross_team = 0
        cross_dept = 0
        if degree > 0:
            for neighbor in G_u.neighbors(emp):
                if emp_dict[neighbor]['team'] != info['team']:
                    cross_team += 1
                if emp_dict[neighbor]['department'] != info['department']:
                    cross_dept += 1

        cross_team_ratio = cross_team / degree if degree > 0 else 0
        cross_department_ratio = cross_dept / degree if degree > 0 else 0

        feature_data.append({
            'time_id': t, 'employee_id': emp, 'name': info['name'],
            'department': info['department'], 'team': info['team'],
            'job_level': job_level, 'is_manager': is_manager,
            'degree': degree, 'weighted_degree': weighted_degree,
            'degree_centrality': d_cent, 'betweenness_centrality': b_cent,
            'eigenvector_centrality': e_cent, 'out_degree': out_degree,
            'in_degree': in_degree, 'cross_team_degree': cross_team,
            'cross_department_degree': cross_dept,
            'cross_team_ratio': cross_team_ratio,
            'cross_department_ratio': cross_department_ratio
        })

df_all = pd.DataFrame(feature_data)

# ==========================================
# 4. 학습 데이터셋 (Target 병합)
# ==========================================
# t+1 시점의 degree를 가져오기 위한 Shift 연산
df_all = df_all.sort_values(by=['employee_id', 'time_id'])
df_all['degree_t1'] = df_all.groupby('employee_id')['degree'].shift(-1)

# 학습 데이터: 마지막 시점 T를 제외한 모든 시점
last_t = time_ids[-1]
train_df = df_all[df_all['time_id'] != last_t].copy()

# 이탈 위험 (Target) 정의
train_df['degree_drop_ratio'] = np.where(
    train_df['degree'] > 0,
    (train_df['degree'] - train_df['degree_t1']) / train_df['degree'],
    0
)
train_df['exit_risk_next'] = (train_df['degree_drop_ratio'] >= 0.5).astype(int)

# 모델에 사용할 피처 리스트
features = [
    'job_level', 'is_manager', 'degree', 'weighted_degree', 'degree_centrality',
    'betweenness_centrality', 'eigenvector_centrality', 'out_degree', 'in_degree',
    'cross_team_degree', 'cross_department_degree', 'cross_team_ratio', 'cross_department_ratio'
]

X_train = train_df[features]
y_train = train_df['exit_risk_next']

# ==========================================
# 5. 모델 학습 (Logistic Regression)
# ==========================================
print("로지스틱 회귀 모델 학습 중...")
model = LogisticRegression(max_iter=3000, random_state=42, class_weight='balanced')
model.fit(X_train, y_train)

train_pred_prob = model.predict_proba(X_train)[:, 1]
train_auc = roc_auc_score(y_train, train_pred_prob)

# ==========================================
# 6. 다음 분기 (T+1) 예측
# ==========================================
test_df = df_all[df_all['time_id'] == last_t].copy()
X_test = test_df[features]

test_df['predicted_exit_risk_probability'] = model.predict_proba(X_test)[:, 1]

# 예측 확률 내림차순 정렬 (상위 위험군 도출)
test_df = test_df.sort_values(by='predicted_exit_risk_probability', ascending=False)
top_10_risk = test_df.head(10)

# ==========================================
# 7. 결과 출력
# ==========================================
print("\n" + "=" * 60)
print("[1] 분석 기준")
print("=" * 60)
print("- 분석 단위: employee-time 단위 예측")
print("- 타겟 정의: 다음 분기 degree가 50% 이상 감소하면 이탈 위험(exit_risk_next=1)으로 분류")
print("- 중심성 지표는 Undirected 통합 기준, 송/수신 지표는 Directed 분리 기준으로 산출")

print("\n" + "=" * 60)
print("[2] 학습 데이터 요약")
print("=" * 60)
print(f"- 학습 샘플 수: {len(train_df):,} 건 (시점: {time_ids[:-1]})")
print(f"- 실제 이탈 위험(Target=1) 발생 비율: {y_train.mean():.2%}")
print(f"- 모델 Train ROC AUC Score: {train_auc:.4f}")

print("\n" + "=" * 60)
print("[3] 모델 계수 (어떤 피처가 이탈 위험을 높이는가?)")
print("=" * 60)
coef_df = pd.DataFrame({'Feature': features, 'Coefficient': model.coef_[0]})
coef_df = coef_df.sort_values(by='Coefficient', ascending=False)
print(coef_df.round(4).to_string(index=False))

print("\n" + "=" * 60)
print(f"[4] 다음 분기 네트워크 이탈 위험 상위 10명 (기준: {last_t})")
print("=" * 60)
display_cols = ['employee_id', 'name', 'department', 'predicted_exit_risk_probability', 'degree', 'degree_drop_ratio']
# 예측 데이터에는 drop ratio가 없으므로 화면 출력용 컬럼만 지정
print(
    test_df[['employee_id', 'name', 'department', 'team', 'predicted_exit_risk_probability', 'degree']].head(10).round(
        4).to_string(index=False))

print("\n" + "=" * 60)
print("[5] 해석 가이드")
print("=" * 60)
print("- Predicted Probability: 이 수치가 높을수록 다음 분기에 타인과의 커뮤니케이션 연결(Degree)이 반토막 날 확률이 높습니다.")
print("- Coefficient(양수): 이 값이 높은 직원은 소통이 급감할(이탈할) 위험성이 큽니다. (예: 특정 팀에만 고립된 경우 등)")
print("- Coefficient(음수): 이 값이 높은 직원은 안정적으로 네트워크를 유지하는 경향이 있습니다.")

print("\n" + "=" * 60)
print("[6] 최종 판정")
print("=" * 60)
if not top_10_risk.empty:
    top1 = top_10_risk.iloc[0]
    print(f">>> 다음 분기에 네트워크 이탈 위험(=degree 급감 위험)이 높은 직원 후보를 도출했습니다.")
    print(f" - 1위 후보 직원: {top1['employee_id']} ({top1['name']})")
    print(f" - 예측 확률: {top1['predicted_exit_risk_probability']:.2%}")
    print(f" - 현재 소통자 수(degree): {top1['degree']}")
    print(f" - 총 교류량(weighted_degree): {top1['weighted_degree']}")
    print(f" - 타 팀 교류 비율(cross_team_ratio): {top1['cross_team_ratio']:.2%}")
    print(f" - 타 부서 교류 비율(cross_department_ratio): {top1['cross_department_ratio']:.2%}")
    print(f" - 매개 중심성(betweenness): {top1['betweenness_centrality']:.4f}")
    print(f" - 위세 중심성(eigenvector): {top1['eigenvector_centrality']:.4f}")
else:
    print(">>> 데이터가 부족하여 후보를 도출할 수 없습니다.")

# ==========================================
# 8. 파일 저장 (CSV)
# ==========================================
output_csv = os.path.join(base_dir, "SNA_다음분기_네트워크_이탈위험_예측.csv")

# 저장용 컬럼 정리
save_cols = ['time_id', 'employee_id', 'name', 'department', 'team', 'predicted_exit_risk_probability'] + features
test_df[save_cols].to_csv(output_csv, index=False, encoding='utf-8-sig')

print(f"\n✓ 성공: 다음 분기 이탈 위험 예측 결과가 CSV 파일로 저장되었습니다.\n저장 경로: {output_csv}")