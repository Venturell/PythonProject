# ============================================================
# Organizational Reorganization Impact Analysis (IT Department)
# ============================================================

import pandas as pd
import numpy as np
import networkx as nx
import re
from pathlib import Path
from networkx.algorithms.community import (
    greedy_modularity_communities,
    modularity
)

# ------------------------------------------------------------
# 파일 경로
# ------------------------------------------------------------

file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#7\7_PAproject_7_3_SNA.xlsx"

REORG_TIME = "2024Q3"
TARGET_DEPARTMENT = "IT"

# ------------------------------------------------------------
# 데이터 로드
# ------------------------------------------------------------

employees = pd.read_excel(file_path, sheet_name="employees")
edges = pd.read_excel(file_path, sheet_name="edges")
events = pd.read_excel(file_path, sheet_name="events")

print("=" * 80)
print("ORGANIZATIONAL REORGANIZATION IMPACT ANALYSIS")
print("=" * 80)

# ------------------------------------------------------------
# time_id 정렬 함수
# ------------------------------------------------------------

def parse_time_id(x):

    x = str(x).strip().upper()

    match = re.search(r"(\d{4})\D*Q(\d+)", x)

    if not match:
        raise ValueError(f"잘못된 time_id 형식: {x}")

    return (
        int(match.group(1)),
        int(match.group(2))
    )

# ------------------------------------------------------------
# 직원 ID 타입 통일
# ------------------------------------------------------------

employees["employee_id"] = employees["employee_id"].astype(str)

edges["source"] = edges["source"].astype(str)
edges["target"] = edges["target"].astype(str)

# ------------------------------------------------------------
# communication만 사용
# ------------------------------------------------------------

edges = edges[
    edges["tie_type"] == "communication"
].copy()

# 자기 자신 제거

edges = edges[
    edges["source"] != edges["target"]
].copy()

# 직원 존재 여부 확인

valid_ids = set(
    employees["employee_id"]
)

edges = edges[
    edges["source"].isin(valid_ids)
    &
    edges["target"].isin(valid_ids)
].copy()

# ------------------------------------------------------------
# 직원 정보 매핑
# ------------------------------------------------------------

emp_info = employees[
    [
        "employee_id",
        "name",
        "department",
        "team"
    ]
].copy()

source_map = emp_info.rename(
    columns={
        "employee_id": "source",
        "department": "source_department",
        "team": "source_team"
    }
)

target_map = emp_info.rename(
    columns={
        "employee_id": "target",
        "department": "target_department",
        "team": "target_team"
    }
)

edges = edges.merge(
    source_map,
    on="source",
    how="left"
)

edges = edges.merge(
    target_map,
    on="target",
    how="left"
)

# ------------------------------------------------------------
# 조직개편 이벤트 확인
# ------------------------------------------------------------

event_check = events[
    (events["event_type"] == "reorganization")
    &
    (events["time_id"].astype(str).str.upper() == REORG_TIME)
    &
    (events["affected_department"] == TARGET_DEPARTMENT)
].copy()

# ------------------------------------------------------------
# pre / post 구분
# ------------------------------------------------------------

edges["period"] = np.where(
    edges["time_id"].apply(parse_time_id)
    <
    parse_time_id(REORG_TIME),
    "pre",
    "post"
)

# ------------------------------------------------------------
# 분석 함수
# ------------------------------------------------------------

def analyze_network(df):

    if len(df) == 0:
        return {}, pd.DataFrame()

    temp = df.copy()

    temp["node1"] = temp[
        ["source", "target"]
    ].min(axis=1)

    temp["node2"] = temp[
        ["source", "target"]
    ].max(axis=1)

    undirected_edges = (
        temp
        .groupby(
            [
                "node1",
                "node2",
                "source_team",
                "target_team"
            ],
            as_index=False
        )["interaction_count"]
        .sum()
    )

    G = nx.Graph()

    for _, row in undirected_edges.iterrows():

        G.add_edge(
            row["node1"],
            row["node2"],
            weight=row["interaction_count"]
        )

    number_of_nodes = G.number_of_nodes()
    number_of_edges = G.number_of_edges()

    density = (
        nx.density(G)
        if number_of_nodes > 1
        else 0
    )

    degrees = dict(G.degree())

    weighted_degrees = dict(
        G.degree(weight="weight")
    )

    average_degree = (
        np.mean(list(degrees.values()))
        if len(degrees) > 0
        else 0
    )

    average_weighted_degree = (
        np.mean(list(weighted_degrees.values()))
        if len(weighted_degrees) > 0
        else 0
    )

    undirected_edges["tie_type2"] = np.where(
        undirected_edges["source_team"]
        ==
        undirected_edges["target_team"],
        "within",
        "between"
    )

    within_team_ties = (
        undirected_edges["tie_type2"]
        .eq("within")
        .sum()
    )

    between_team_ties = (
        undirected_edges["tie_type2"]
        .eq("between")
        .sum()
    )

    total_ties = len(undirected_edges)

    within_team_ratio = (
        within_team_ties / total_ties
        if total_ties > 0
        else 0
    )

    between_team_ratio = (
        between_team_ties / total_ties
        if total_ties > 0
        else 0
    )

    team_map = (
        employees
        .set_index("employee_id")["team"]
        .to_dict()
    )

    nx.set_node_attributes(
        G,
        team_map,
        "team"
    )

    try:
        team_assortativity = (
            nx.attribute_assortativity_coefficient(
                G,
                "team"
            )
        )
    except:
        team_assortativity = np.nan

    communities_real = []

    for team_name, grp in employees.groupby("team"):
        nodes = set(
            grp["employee_id"]
        )

        nodes = nodes.intersection(
            set(G.nodes())
        )

        if len(nodes) > 0:
            communities_real.append(nodes)

    try:
        team_modularity = modularity(
            G,
            communities_real,
            weight="weight"
        )
    except:
        team_modularity = np.nan

    try:
        detected = list(
            greedy_modularity_communities(
                G,
                weight="weight"
            )
        )

        detected_modularity = modularity(
            G,
            detected,
            weight="weight"
        )

        num_detected = len(detected)

    except:
        detected_modularity = np.nan
        num_detected = np.nan

    summary = {
        "number_of_nodes": number_of_nodes,
        "number_of_edges": number_of_edges,
        "total_ties": total_ties,
        "within_team_ties": within_team_ties,
        "between_team_ties": between_team_ties,
        "within_team_ratio": round(within_team_ratio, 4),
        "between_team_ratio": round(between_team_ratio, 4),
        "density": round(density, 4),
        "average_degree": round(average_degree, 4),
        "average_weighted_degree": round(
            average_weighted_degree,
            4
        ),
        "team_assortativity": round(
            team_assortativity,
            4
        ),
        "team_modularity": round(
            team_modularity,
            4
        ),
        "detected_community_modularity": round(
            detected_modularity,
            4
        ),
        "num_detected_communities": num_detected
    }

    matrix = pd.pivot_table(
        df,
        index="source_team",
        columns="target_team",
        values="interaction_count",
        aggfunc="sum",
        fill_value=0
    )

    return summary, matrix

# ------------------------------------------------------------
# IT 분석 함수
# ------------------------------------------------------------

def analyze_it(df):

    it_related = df[
        (df["source_department"] == "IT")
        |
        (df["target_department"] == "IT")
    ]

    it_internal = df[
        (df["source_department"] == "IT")
        &
        (df["target_department"] == "IT")
    ]

    it_outbound = df[
        (df["source_department"] == "IT")
        &
        (df["target_department"] != "IT")
    ]

    it_inbound = df[
        (df["source_department"] != "IT")
        &
        (df["target_department"] == "IT")
    ]

    it_cross = pd.concat(
        [it_outbound, it_inbound]
    )

    related = len(it_related)

    return {
        "it_related_ties": related,
        "it_internal_ties": len(it_internal),
        "it_outbound_ties": len(it_outbound),
        "it_inbound_ties": len(it_inbound),
        "it_cross_dept_ties": len(it_cross),
        "it_internal_ratio":
            round(len(it_internal)/related,4)
            if related > 0 else 0,
        "it_cross_dept_ratio":
            round(len(it_cross)/related,4)
            if related > 0 else 0
    }

# ------------------------------------------------------------
# 분석 수행
# ------------------------------------------------------------

pre_df = edges[
    edges["period"] == "pre"
]

post_df = edges[
    edges["period"] == "post"
]

pre_summary, pre_matrix = analyze_network(pre_df)
post_summary, post_matrix = analyze_network(post_df)

pre_it = analyze_it(pre_df)
post_it = analyze_it(post_df)

summary_df = pd.DataFrame(
    [pre_summary, post_summary],
    index=["PRE", "POST"]
)

it_df = pd.DataFrame(
    [pre_it, post_it],
    index=["PRE", "POST"]
)

comparison_df = pd.concat(
    [
        summary_df.T,
        it_df.T
    ],
    axis=0
)

# ------------------------------------------------------------
# 최종 판정
# ------------------------------------------------------------

change_flag = False

try:

    if (
        post_summary["between_team_ratio"]
        -
        pre_summary["between_team_ratio"]
    ) > 0.05:
        change_flag = True

    if (
        post_summary["team_assortativity"]
        -
        pre_summary["team_assortativity"]
    ) < -0.05:
        change_flag = True

    if (
        post_summary["team_modularity"]
        -
        pre_summary["team_modularity"]
    ) < -0.05:
        change_flag = True

    if (
        post_summary["density"]
        -
        pre_summary["density"]
    ) > 0.01:
        change_flag = True

    if (
        post_it["it_cross_dept_ratio"]
        -
        pre_it["it_cross_dept_ratio"]
    ) > 0.05:
        change_flag = True

except:
    pass

if change_flag:
    final_judgement = (
        "조직개편 이후 연결 구조가 바뀌었을 가능성이 있습니다."
    )
else:
    final_judgement = (
        "조직개편 전후 연결 구조 변화가 아주 뚜렷하지는 않습니다."
    )

# ------------------------------------------------------------
# 출력
# ------------------------------------------------------------

print("\n[분석 기준]")
print("Communication Network")
print("REORG_TIME =", REORG_TIME)

print("\n[조직개편 이벤트 확인]")
print(event_check)

print("\n[전체 요약]")
print(summary_df)

print("\n[전후 비교 테이블]")
print(comparison_df)

print("\n[IT 관련 상세 비교]")
print(it_df)

print("\n[PRE 팀-팀 매트릭스]")
print(pre_matrix)

print("\n[POST 팀-팀 매트릭스]")
print(post_matrix)

print("\n[해석 가이드]")
print("between_team_ratio 증가 → 부서 간 협업 증가")
print("team_assortativity 감소 → 팀 경계 약화")
print("team_modularity 감소 → 사일로 약화")
print("density 증가 → 연결성 증가")
print("it_cross_dept_ratio 증가 → IT 협업 범위 확대")

print("\n[최종 판정]")
print(final_judgement)

# ------------------------------------------------------------
# Excel 저장
# ------------------------------------------------------------

output_file = (
    Path(file_path).parent
    /
    "Reorganization_Impact_Analysis.xlsx"
)

with pd.ExcelWriter(
    output_file,
    engine="openpyxl"
) as writer:

    summary_df.to_excel(
        writer,
        sheet_name="전체요약"
    )

    comparison_df.to_excel(
        writer,
        sheet_name="전후비교"
    )

    it_df.to_excel(
        writer,
        sheet_name="IT상세비교"
    )

    pre_matrix.to_excel(
        writer,
        sheet_name="PRE_팀매트릭스"
    )

    post_matrix.to_excel(
        writer,
        sheet_name="POST_팀매트릭스"
    )

    event_check.to_excel(
        writer,
        sheet_name="조직개편이벤트",
        index=False
    )

print("\nExcel 저장 완료")
print(output_file)