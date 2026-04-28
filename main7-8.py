import pandas as pd
import numpy as np
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. 파일 경로 및 환경 설정 ---
# ==========================================
EXCEL_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"
BASE_DIR = os.path.dirname(EXCEL_PATH)

print("데이터를 로드하고 동적 네트워크(Dynamic SNA) 분석을 시작합니다...\n")

# ==========================================
# --- 2. 데이터 로드 및 전처리 ---
# ==========================================
df_emp = pd.read_excel(EXCEL_PATH, sheet_name='employees')
df_edges_raw = pd.read_excel(EXCEL_PATH, sheet_name='edges')

valid_ids = set(df_emp['employee_id'])

# 필터링: communication, 자기 자신 제외, 유효한 직원
df_filtered = df_edges_raw[
    (df_edges_raw['tie_type'] == 'communication') &
    (df_edges_raw['source'] != df_edges_raw['target']) &
    (df_edges_raw['source'].isin(valid_ids)) &
    (df_edges_raw['target'].isin(valid_ids))
    ].copy()

# Directed Dyad 단위 집계: 같은 시점, 같은 source->target은 interaction_count 합산
df_agg = df_filtered.groupby(['time_id', 'source', 'target'])['interaction_count'].sum().reset_index()

# 시간대 정렬
time_ids = sorted(df_agg['time_id'].unique())

# ==========================================
# --- 3. 직원 속성 매핑 도구 준비 ---
# ==========================================
name_map = dict(zip(df_emp['employee_id'], df_emp['name']))
dept_map = dict(zip(df_emp['employee_id'], df_emp['department']))
team_map = dict(zip(df_emp['employee_id'], df_emp['team']))


def add_attributes(df):
    """source와 target에 직원 속성(이름, 부서, 팀)을 매핑하는 함수"""
    if df.empty: return df
    df['source_name'] = df['source'].map(name_map)
    df['source_dept'] = df['source'].map(dept_map)
    df['source_team'] = df['source'].map(team_map)
    df['target_name'] = df['target'].map(name_map)
    df['target_dept'] = df['target'].map(dept_map)
    df['target_team'] = df['target'].map(team_map)
    return df


# ==========================================
# --- 4. 시점 간 전이(Transition) 분석 ---
# ==========================================
summary_data = []
persisted_list = []
dissolved_list = []
formed_list = []

for i in range(len(time_ids) - 1):
    t = time_ids[i]
    t_next = time_ids[i + 1]

    # t 시점과 t+1 시점의 데이터 분리
    df_t = df_agg[df_agg['time_id'] == t]
    df_t_next = df_agg[df_agg['time_id'] == t_next]

    # Dyad 집합 생성 (set of tuples)
    set_t = set(zip(df_t['source'], df_t['target']))
    set_t_next = set(zip(df_t_next['source'], df_t_next['target']))

    # 지표 1~5 계산
    ties_t = len(set_t)
    ties_t_1 = len(set_t_next)

    persisted = set_t.intersection(set_t_next)
    dissolved = set_t - set_t_next
    formed = set_t_next - set_t

    # 지표 6~8 계산 (ZeroDivisionError 방지)
    persistence_rate = len(persisted) / ties_t if ties_t > 0 else 0
    dissolution_rate = len(dissolved) / ties_t if ties_t > 0 else 0
    formation_rate = len(formed) / ties_t_1 if ties_t_1 > 0 else 0

    # 요약 데이터 추가
    summary_data.append({
        'transition': f"{t} -> {t_next}",
        'ties_t': ties_t,
        'ties_t_1': ties_t_1,
        'persisted_ties': len(persisted),
        'dissolved_ties': len(dissolved),
        'formed_ties': len(formed),
        'persistence_rate': round(persistence_rate, 4),
        'dissolution_rate': round(dissolution_rate, 4),
        'formation_rate': round(formation_rate, 4)
    })

    # 상세 목록 추가 (데이터프레임 생성용)
    for s, tgt in persisted:
        int_t = df_t[(df_t['source'] == s) & (df_t['target'] == tgt)]['interaction_count'].values[0]
        int_t_next = df_t_next[(df_t_next['source'] == s) & (df_t_next['target'] == tgt)]['interaction_count'].values[0]
        persisted_list.append({'transition': f"{t} -> {t_next}", 'source': s, 'target': tgt, 'interaction_t': int_t,
                               'interaction_t_1': int_t_next})

    for s, tgt in dissolved:
        int_t = df_t[(df_t['source'] == s) & (df_t['target'] == tgt)]['interaction_count'].values[0]
        dissolved_list.append({'transition': f"{t} -> {t_next}", 'source': s, 'target': tgt, 'interaction_t': int_t})

    for s, tgt in formed:
        int_t_next = df_t_next[(df_t_next['source'] == s) & (df_t_next['target'] == tgt)]['interaction_count'].values[0]
        formed_list.append(
            {'transition': f"{t} -> {t_next}", 'source': s, 'target': tgt, 'interaction_t_1': int_t_next})

# DataFrame 변환 및 속성 매핑
summary_df = pd.DataFrame(summary_data)
persisted_ties_df = add_attributes(pd.DataFrame(persisted_list))
dissolved_ties_df = add_attributes(pd.DataFrame(dissolved_list))
formed_ties_df = add_attributes(pd.DataFrame(formed_list))

# ==========================================
# --- 5. 관계 이력(Tie History) 테이블 생성 ---
# ==========================================
# source-target 조합별로 각 time_id에 존재하는지 1/0으로 피벗
tie_history = df_agg.assign(exists=1).pivot_table(
    index=['source', 'target'],
    columns='time_id',
    values='exists',
    fill_value=0
).reset_index()

# 총 유지 기간(기간 수 합산) 계산
tie_history['total_active_periods'] = tie_history[time_ids].sum(axis=1)
tie_history = add_attributes(tie_history)
tie_history = tie_history.sort_values(by='total_active_periods', ascending=False).reset_index(drop=True)

# ==========================================
# --- 6. 콘솔 출력 및 결과 판정 ---
# ==========================================
print("=" * 80)
print("1. [분석 기준]")
print(" - 대상: 유효 직원 간의 'Communication' 네트워크 (자기 자신 제외)")
print(" - 단위: Directed Dyad (Source -> Target)")
print(" - 상호작용: 동일 시점 내 중복 연결은 interaction_count로 합산")
print("-" * 80)

print(f"2. [분석 대상 time_id 목록]: {', '.join(time_ids)}")
print("-" * 80)

print("3. [시점 간 전이 요약]")
print(summary_df.to_string(index=False))
print("-" * 80)

print("4. [해석 가이드]")
print(" - Persistence Rate (유지율): 이전 시점의 관계 중 다음 시점에도 살아남은 비율")
print(" - Dissolution Rate (소멸율): 이전 시점의 관계 중 다음 시점에 끊어진 비율")
print(" - Formation Rate (형성율): 다음 시점의 전체 관계 중 새롭게 만들어진 관계의 비율")
print("-" * 80)

print("5. [가장 오래 지속된 관계 상위 15개]")
display_cols = ['source_name', 'source_team', 'target_name', 'target_team', 'total_active_periods']
print(tie_history.head(15)[display_cols].to_string(index=False))
print("-" * 80)

print("6. [가장 최근 전이에서 사라진 관계 상위 15개 (이전 시점 interaction 기준)]")
if not dissolved_ties_df.empty:
    last_transition = summary_df.iloc[-1]['transition']
    recent_dissolved = dissolved_ties_df[dissolved_ties_df['transition'] == last_transition]
    recent_dissolved = recent_dissolved.sort_values(by='interaction_t', ascending=False).head(15)
    d_cols = ['source_name', 'source_team', 'target_name', 'target_team', 'interaction_t']
    print(recent_dissolved[d_cols].to_string(index=False))
else:
    print("사라진 관계가 없습니다.")
print("-" * 80)

# 최종 판정 로직
avg_persistence = summary_df['persistence_rate'].mean()
avg_dissolution = summary_df['dissolution_rate'].mean()

print("7. [최종 판정]")
print(f" - 평균 관계 유지율(Persistence): {avg_persistence:.2f}")
print(f" - 평균 관계 소멸율(Dissolution): {avg_dissolution:.2f}")

if avg_persistence >= 0.6 and avg_dissolution < 0.4:
    print(" 💡 [판결]: 커뮤니케이션 관계는 전반적으로 비교적 안정적으로 유지되고 있습니다.")
elif avg_dissolution >= 0.5:
    print(" 🚨 [판결]: 커뮤니케이션 관계는 시점 간 소멸 비율이 높아 변동성이 큰 편입니다.")
else:
    print(" ⚖️ [판결]: 커뮤니케이션 관계는 일부는 유지되고 일부는 사라지는 중간 수준의 변동성을 보입니다.")
print("=" * 80)

# ==========================================
# --- 7. 결과 파일 저장 ---
# ==========================================
out_files = {
    "2025Q2_DynamicSNA_Summary.csv": summary_df,
    "2025Q2_DynamicSNA_Persisted.csv": persisted_ties_df,
    "2025Q2_DynamicSNA_Dissolved.csv": dissolved_ties_df,
    "2025Q2_DynamicSNA_Formed.csv": formed_ties_df,
    "2025Q2_DynamicSNA_History.csv": tie_history
}

for filename, df in out_files.items():
    if not df.empty:
        filepath = os.path.join(BASE_DIR, filename)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')

print(f"\n✅ 5개의 분석 결과 파일이 성공적으로 저장되었습니다.\n저장 경로: {BASE_DIR}")