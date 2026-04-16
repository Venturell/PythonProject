import pandas as pd
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. 파일 경로 설정 ---
# ==========================================
EXCEL_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"

# 저장할 CSV 파일 경로 (같은 폴더에 저장)
dir_name = os.path.dirname(EXCEL_PATH)
OUTPUT_CSV = os.path.join(dir_name, "2025Q2_Top_Insiders.csv")

print("데이터를 불러오고 분석을 시작합니다...\n")

# ==========================================
# --- 2. 데이터 로드 및 전처리 ---
# ==========================================
df_emp = pd.read_excel(EXCEL_PATH, sheet_name='employees')
df_edges = pd.read_excel(EXCEL_PATH, sheet_name='edges')

# 조건 1: 2025Q2 시점 필터링
# 조건 2: 자기 자신과의 연결(source == target) 제거
edges_q2 = df_edges[(df_edges['time_id'] == '2025Q2') & (df_edges['source'] != df_edges['target'])].copy()

# ==========================================
# --- 3. SNA 핵심 지표 계산 ---
# ==========================================

# 1) out_degree: 각 직원이 먼저 연락/협업을 시도한 고유 상대방 수
out_degree = edges_q2.groupby('source')['target'].nunique().rename('out_degree')

# 2) in_degree: 각 직원에게 연락/협업을 요청해 온 고유 상대방 수
in_degree = edges_q2.groupby('target')['source'].nunique().rename('in_degree')

# 3) total_interaction: 전체 상호작용 빈도 (보낸 횟수 + 받은 횟수)
sent_interaction = edges_q2.groupby('source')['interaction_count'].sum().rename('sent_int')
received_interaction = edges_q2.groupby('target')['interaction_count'].sum().rename('received_int')

# 4) total_unique_connections: 방향과 상관없이 연결된 전체 고유 상대방 수 (Undirected 관점)
# 소스와 타겟을 한 줄로 나열하여 양방향 관계를 하나로 통합 후 고유값 계산
df_source = edges_q2[['source', 'target']].rename(columns={'source': 'emp_id', 'target': 'partner'})
df_target = edges_q2[['target', 'source']].rename(columns={'target': 'emp_id', 'source': 'partner'})
df_combined = pd.concat([df_source, df_target])

total_unique_connections = df_combined.groupby('emp_id')['partner'].nunique().rename('total_unique_connections')

# ==========================================
# --- 4. 지표 통합 및 직원 정보 병합 ---
# ==========================================
# 지표들을 하나의 데이터프레임으로 병합
metrics_df = pd.concat([
    total_unique_connections,
    out_degree,
    in_degree,
    sent_interaction,
    received_interaction
], axis=1).fillna(0)

# 파생변수: total_interaction 계산 (소수점 방지를 위해 정수형 변환)
metrics_df['total_interaction'] = (metrics_df['sent_int'] + metrics_df['received_int']).astype(int)
metrics_df['total_unique_connections'] = metrics_df['total_unique_connections'].astype(int)
metrics_df['out_degree'] = metrics_df['out_degree'].astype(int)
metrics_df['in_degree'] = metrics_df['in_degree'].astype(int)

# 불필요한 중간 계산 컬럼 제거
metrics_df = metrics_df.drop(columns=['sent_int', 'received_int'])
metrics_df.index.name = 'employee_id'

# 직원 기본 정보(employees)와 병합 (필요한 컬럼만 추출)
emp_cols = ['employee_id', 'name', 'department', 'team', 'job_level', 'is_manager']
final_df = pd.merge(df_emp[emp_cols], metrics_df, on='employee_id', how='inner')

# ==========================================
# --- 5. 정렬, 순위 부여 및 결과 출력 ---
# ==========================================
# 정렬 기준: 1순위 unique_connections, 2순위 total_interaction, 3순위 out_degree
final_df = final_df.sort_values(
    by=['total_unique_connections', 'total_interaction', 'out_degree'],
    ascending=[False, False, False]
).reset_index(drop=True)

# Rank 컬럼 추가
final_df.insert(0, 'rank', final_df.index + 1)

# 상위 10명 추출
top_10_insiders = final_df.head(10)

# 결과 출력
print("=" * 90)
print("🏆 2025 Q2 사내 최고 인사이더 (Top 10)")
print("=" * 90)
# 보기 좋게 특정 컬럼만 콘솔에 출력
display_cols = ['rank', 'name', 'department', 'job_level', 'total_unique_connections', 'total_interaction', 'out_degree', 'in_degree']
print(top_10_insiders[display_cols].to_string(index=False))
print("=" * 90)

# CSV로 전체 결과 저장 (한글 깨짐 방지를 위해 utf-8-sig 사용)
final_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
print(f"\n✅ 전체 직원 네트워크 분석 결과가 CSV로 저장되었습니다.\n저장 경로: {OUTPUT_CSV}")