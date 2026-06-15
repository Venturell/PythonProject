# ============================================================
# Dynamic Social Network Analysis (Communication Tie Dynamics)
# ============================================================

import pandas as pd
import numpy as np
import re
from pathlib import Path

# ------------------------------------------------------------
# 1. 파일 불러오기
# ------------------------------------------------------------

file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"

employees = pd.read_excel(file_path, sheet_name="employees")
edges = pd.read_excel(file_path, sheet_name="edges")

print("=" * 80)
print("Communication Dynamic Network Analysis")
print("=" * 80)

# ------------------------------------------------------------
# 2. 데이터 전처리
# ------------------------------------------------------------

# communication만 사용
edges = edges[edges["tie_type"] == "communication"].copy()

# 자기 자신 제거
edges = edges[edges["source"] != edges["target"]].copy()

# 데이터 타입 통일
employees["employee_id"] = employees["employee_id"].astype(str)
edges["source"] = edges["source"].astype(str)
edges["target"] = edges["target"].astype(str)

# employees에 존재하는 직원만 유지
valid_ids = set(employees["employee_id"])

edges = edges[
    edges["source"].isin(valid_ids)
    & edges["target"].isin(valid_ids)
].copy()

# ------------------------------------------------------------
# 직원 정보 매핑
# ------------------------------------------------------------

emp_info = employees[
    ["employee_id", "name", "department", "team"]
].copy()

source_map = emp_info.rename(
    columns={
        "employee_id": "source",
        "name": "source_name",
        "department": "source_department",
        "team": "source_team"
    }
)

target_map = emp_info.rename(
    columns={
        "employee_id": "target",
        "name": "target_name",
        "department": "target_department",
        "team": "target_team"
    }
)

edges = edges.merge(source_map, on="source", how="left")
edges = edges.merge(target_map, on="target", how="left")

# ------------------------------------------------------------
# time_id 정렬 함수
# ------------------------------------------------------------

def parse_time_id(x):

    x = str(x).strip().upper()

    match = re.search(r"(\d{4})\D*Q(\d+)", x)

    if not match:
        raise ValueError(f"잘못된 time_id 형식: {x}")

    year = int(match.group(1))
    quarter = int(match.group(2))

    return (year, quarter)

time_list = sorted(
    edges["time_id"].dropna().unique(),
    key=parse_time_id
)

# ------------------------------------------------------------
# 동일 시점 동일 source-target 통합
# ------------------------------------------------------------

edges_agg = (
    edges
    .groupby(
        ["time_id", "source", "target"],
        as_index=False
    )["interaction_count"]
    .sum()
)

# ------------------------------------------------------------
# 시점별 directed tie set 생성
# ------------------------------------------------------------

time_ties = {}

for t in time_list:

    temp = edges_agg[
        edges_agg["time_id"] == t
    ]

    tie_set = set(
        zip(
            temp["source"],
            temp["target"]
        )
    )

    time_ties[t] = tie_set

# ------------------------------------------------------------
# 시점 간 전이 분석
# ------------------------------------------------------------

summary_rows = []

persisted_records = []
dissolved_records = []
formed_records = []

for i in range(len(time_list) - 1):

    t = time_list[i]
    t1 = time_list[i + 1]

    ties_t = time_ties[t]
    ties_t1 = time_ties[t1]

    persisted = ties_t.intersection(ties_t1)
    dissolved = ties_t - ties_t1
    formed = ties_t1 - ties_t

    ties_t_count = len(ties_t)
    ties_t1_count = len(ties_t1)

    persisted_count = len(persisted)
    dissolved_count = len(dissolved)
    formed_count = len(formed)

    persistence_rate = (
        persisted_count / ties_t_count
        if ties_t_count > 0 else 0
    )

    dissolution_rate = (
        dissolved_count / ties_t_count
        if ties_t_count > 0 else 0
    )

    formation_rate = (
        formed_count / ties_t1_count
        if ties_t1_count > 0 else 0
    )

    summary_rows.append({
        "time_t": t,
        "time_t1": t1,
        "ties_t": ties_t_count,
        "ties_t1": ties_t1_count,
        "persisted_ties": persisted_count,
        "dissolved_ties": dissolved_count,
        "formed_ties": formed_count,
        "persistence_rate": round(persistence_rate, 4),
        "dissolution_rate": round(dissolution_rate, 4),
        "formation_rate": round(formation_rate, 4)
    })

    for s, tg in persisted:
        persisted_records.append({
            "time_t": t,
            "time_t1": t1,
            "source": s,
            "target": tg
        })

    for s, tg in dissolved:
        dissolved_records.append({
            "time_t": t,
            "time_t1": t1,
            "source": s,
            "target": tg
        })

    for s, tg in formed:
        formed_records.append({
            "time_t": t,
            "time_t1": t1,
            "source": s,
            "target": tg
        })

summary_df = pd.DataFrame(summary_rows)

persisted_ties_df = pd.DataFrame(persisted_records)
dissolved_ties_df = pd.DataFrame(dissolved_records)
formed_ties_df = pd.DataFrame(formed_records)

# ------------------------------------------------------------
# 직원 정보 매핑
# ------------------------------------------------------------

if len(persisted_ties_df) > 0:
    persisted_ties_df = persisted_ties_df.merge(
        source_map,
        on="source",
        how="left"
    ).merge(
        target_map,
        on="target",
        how="left"
    )

if len(dissolved_ties_df) > 0:
    dissolved_ties_df = dissolved_ties_df.merge(
        source_map,
        on="source",
        how="left"
    ).merge(
        target_map,
        on="target",
        how="left"
    )

if len(formed_ties_df) > 0:
    formed_ties_df = formed_ties_df.merge(
        source_map,
        on="source",
        how="left"
    ).merge(
        target_map,
        on="target",
        how="left"
    )

# ------------------------------------------------------------
# 관계 이력 생성
# ------------------------------------------------------------

tie_history = edges_agg.copy()

tie_history_summary = (
    tie_history
    .groupby(
        ["source", "target"],
        as_index=False
    )
    .agg(
        appearance_count=("time_id", "nunique"),
        total_interaction=("interaction_count", "sum")
    )
)

tie_history_summary = tie_history_summary.merge(
    source_map,
    on="source",
    how="left"
)

tie_history_summary = tie_history_summary.merge(
    target_map,
    on="target",
    how="left"
)

# ------------------------------------------------------------
# 가장 오래 지속된 관계
# ------------------------------------------------------------

longest_relationships = (
    tie_history_summary
    .sort_values(
        ["appearance_count", "total_interaction"],
        ascending=[False, False]
    )
    .head(15)
)

# ------------------------------------------------------------
# 최근 전이에서 사라진 관계
# ------------------------------------------------------------

if len(time_list) >= 2:

    latest_t = time_list[-2]
    latest_t1 = time_list[-1]

    latest_dissolved_top15 = dissolved_ties_df[
        (dissolved_ties_df["time_t"] == latest_t)
        &
        (dissolved_ties_df["time_t1"] == latest_t1)
    ].head(15)

else:
    latest_dissolved_top15 = pd.DataFrame()

# ------------------------------------------------------------
# 최종 판정
# ------------------------------------------------------------

avg_persistence = summary_df["persistence_rate"].mean()
avg_dissolution = summary_df["dissolution_rate"].mean()

if (
    avg_persistence >= 0.6
    and avg_dissolution < 0.4
):
    final_judgement = (
        "커뮤니케이션 관계는 전반적으로 비교적 안정적으로 유지되고 있습니다."
    )

elif avg_dissolution >= 0.5:
    final_judgement = (
        "커뮤니케이션 관계는 시점 간 소멸 비율이 높아 변동성이 큰 편입니다."
    )

else:
    final_judgement = (
        "커뮤니케이션 관계는 일부는 유지되고 일부는 사라지는 중간 수준의 변동성을 보입니다."
    )

# ------------------------------------------------------------
# 출력
# ------------------------------------------------------------

print("\n[분석 기준]")
print("tie_type = communication")
print("directed dyad 기준")
print("연속 시점(t → t+1) 전이 분석")

print("\n[분석 대상 time_id]")
print(time_list)

print("\n[시점 간 전이 요약]")
print(summary_df)

print("\n[해석 가이드]")
print("Persistence Rate ↑ : 관계 안정성 높음")
print("Dissolution Rate ↑ : 관계 소멸 많음")
print("Formation Rate ↑ : 새로운 관계 생성 많음")

print("\n[가장 오래 지속된 관계 TOP 15]")
print(longest_relationships)

print("\n[가장 최근 전이에서 사라진 관계 TOP 15]")
print(latest_dissolved_top15)

print("\n[최종 판정]")
print(final_judgement)

# ------------------------------------------------------------
# 저장
# ------------------------------------------------------------

output_dir = Path(file_path).parent

output_file = output_dir / "Communication_Dynamic_SNA_Result.xlsx"

with pd.ExcelWriter(
    output_file,
    engine="openpyxl"
) as writer:

    summary_df.to_excel(
        writer,
        sheet_name="시점간전이요약",
        index=False
    )

    persisted_ties_df.to_excel(
        writer,
        sheet_name="지속된관계목록",
        index=False
    )

    dissolved_ties_df.to_excel(
        writer,
        sheet_name="사라진관계목록",
        index=False
    )

    formed_ties_df.to_excel(
        writer,
        sheet_name="새로형성된관계목록",
        index=False
    )

    tie_history_summary.to_excel(
        writer,
        sheet_name="관계이력요약",
        index=False
    )

print("\nExcel 저장 완료")
print(output_file)