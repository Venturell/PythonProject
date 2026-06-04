import pandas as pd
import numpy as np

from pathlib import Path

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from scipy.stats import zscore

import plotly.graph_objects as go

# =====================================================
# 파일 경로
# =====================================================

file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#11\11_PAproject_11_2_pipeline.xlsx"

output_file = (
    Path(file_path).parent
    / "anomaly_detection.html"
)

# =====================================================
# 데이터 로드
# =====================================================

df = pd.read_excel(
    file_path,
    sheet_name="pipeline"
)

# =====================================================
# 날짜 처리
# =====================================================

df["apply_date"] = pd.to_datetime(
    df["apply_date"],
    errors="coerce"
)

df = df.dropna(subset=["apply_date"])

df["month_period"] = (
    df["apply_date"]
    .dt.to_period("M")
)

df["month_label"] = (
    df["month_period"]
    .astype(str)
)

# =====================================================
# 서류 통과 정의
# =====================================================

stage_text = (
    df["stage"]
    .astype(str)
)

doc_pass = stage_text.str.contains(
    "1차",
    case=False,
    na=False
)

# =====================================================
# KPI 집계
# =====================================================

applicants = (
    df.groupby("month_period")
    .size()
    .rename("applicant_count")
)

document_rate = (
    df.assign(
        doc_pass=doc_pass.astype(int)
    )
    .groupby("month_period")["doc_pass"]
    .mean()
    .rename("document_conversion_rate")
)

final_rate = (
    df.assign(
        hired=(df["result"] == "합격").astype(int)
    )
    .groupby("month_period")["hired"]
    .mean()
    .rename("final_hire_rate")
)

avg_ttf = (
    df[df["result"] == "합격"]
    .groupby("month_period")["time_to_fill"]
    .mean()
    .rename("avg_time_to_fill")
)

kpi = pd.concat(
    [
        applicants,
        document_rate,
        final_rate,
        avg_ttf
    ],
    axis=1
).reset_index()

kpi["month_label"] = (
    kpi["month_period"]
    .astype(str)
)

# =====================================================
# Z-score
# =====================================================

target_cols = [
    "applicant_count",
    "document_conversion_rate",
    "final_hire_rate",
    "avg_time_to_fill"
]

for col in target_cols:

    kpi[f"{col}_z"] = zscore(
        kpi[col],
        nan_policy="omit"
    )

    kpi[f"{col}_anomaly"] = (
        np.abs(
            kpi[f"{col}_z"]
        ) > 2
    )

# =====================================================
# Isolation Forest
# =====================================================

X = (
    kpi[target_cols]
    .fillna(
        kpi[target_cols].median()
    )
)

scaler = StandardScaler()

X_scaled = scaler.fit_transform(X)

iso = IsolationForest(
    contamination=0.1,
    random_state=42
)

kpi["iforest"] = (
    iso.fit_predict(X_scaled)
)

kpi["iforest_flag"] = (
    kpi["iforest"] == -1
)

# =====================================================
# 원인 추정
# =====================================================

def infer_reason(row):

    reasons = []

    for col in target_cols:

        z = row[f"{col}_z"]

        if pd.isna(z):
            continue

        if abs(z) > 2:

            if z > 0:
                reasons.append(
                    f"{col} 급증"
                )
            else:
                reasons.append(
                    f"{col} 급감"
                )

    return ", ".join(reasons)

kpi["reason"] = (
    kpi.apply(
        infer_reason,
        axis=1
    )
)

# =====================================================
# KPI 그래프 생성 함수
# =====================================================

def create_chart(col, title):

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=kpi["month_label"],
            y=kpi[col],
            mode="lines+markers",
            name=title
        )
    )

    anomaly = kpi[
        kpi[f"{col}_anomaly"]
    ]

    fig.add_trace(
        go.Scatter(
            x=anomaly["month_label"],
            y=anomaly[col],
            mode="markers",
            marker=dict(
                size=12,
                color="red"
            ),
            name="Z-score 이상치"
        )
    )

    fig.update_layout(
        template="plotly_white",
        height=500,
        title=title
    )

    return fig

# =====================================================
# 그래프
# =====================================================

fig_applicant = create_chart(
    "applicant_count",
    "월별 지원자 수"
)

fig_doc = create_chart(
    "document_conversion_rate",
    "월별 서류 전환율"
)

fig_final = create_chart(
    "final_hire_rate",
    "월별 최종 합격률"
)

fig_ttf = create_chart(
    "avg_time_to_fill",
    "월별 평균 Time-to-Fill"
)

# =====================================================
# Isolation Forest 그래프
# =====================================================

fig_iforest = go.Figure()

fig_iforest.add_trace(
    go.Scatter(
        x=kpi["month_label"],
        y=kpi["applicant_count"],
        mode="lines+markers",
        name="지원자 수"
    )
)

iso_points = kpi[
    kpi["iforest_flag"]
]

fig_iforest.add_trace(
    go.Scatter(
        x=iso_points["month_label"],
        y=iso_points["applicant_count"],
        mode="markers",
        marker=dict(
            size=14,
            color="orange"
        ),
        name="Isolation Forest"
    )
)

fig_iforest.update_layout(
    template="plotly_white",
    height=600,
    title="Isolation Forest 이상감지"
)

# =====================================================
# 이상치 테이블
# =====================================================

summary = kpi[
    (
        kpi["iforest_flag"]
    )
    |
    (
        kpi[
            [
                f"{c}_anomaly"
                for c in target_cols
            ]
        ].any(axis=1)
    )
]

# =====================================================
# KPI 카드
# =====================================================

total_months = len(kpi)

z_months = (
    kpi[
        [
            f"{c}_anomaly"
            for c in target_cols
        ]
    ]
    .any(axis=1)
    .sum()
)

if_months = (
    kpi["iforest_flag"]
    .sum()
)

both_months = (
    (
        kpi["iforest_flag"]
    )
    &
    (
        kpi[
            [
                f"{c}_anomaly"
                for c in target_cols
            ]
        ]
        .any(axis=1)
    )
).sum()

# =====================================================
# HTML
# =====================================================

html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">

<title>Anomaly Detection Dashboard</title>

<style>

body {{
    font-family: Arial, sans-serif;
    background:#f4f6f9;
    margin:0;
}}

.header {{
    background:#1f4e79;
    color:white;
    padding:20px;
}}

.container {{
    padding:20px;
}}

.cards {{
    display:flex;
    gap:20px;
    margin-bottom:20px;
}}

.card {{
    background:white;
    flex:1;
    padding:20px;
    border-radius:12px;
    box-shadow:0 2px 8px rgba(0,0,0,0.15);
    text-align:center;
}}

.card h2 {{
    margin:0;
}}

.card p {{
    font-size:28px;
    font-weight:bold;
}}

.tab {{
    overflow:hidden;
    background:white;
    border-radius:12px;
    margin-bottom:20px;
}}

.tab button {{
    background:inherit;
    float:left;
    border:none;
    padding:14px 20px;
    cursor:pointer;
}}

.tab button:hover {{
    background:#ddd;
}}

.tabcontent {{
    display:none;
    background:white;
    padding:20px;
    border-radius:12px;
}}

table {{
    width:100%;
    border-collapse:collapse;
}}

th,td {{
    border:1px solid #ddd;
    padding:8px;
}}

th {{
    background:#1f4e79;
    color:white;
}}

</style>

<script>

function openTab(evt, tabName) {{

var i, tabcontent, tablinks;

tabcontent = document.getElementsByClassName("tabcontent");

for (i = 0; i < tabcontent.length; i++) {{
    tabcontent[i].style.display = "none";
}}

tablinks = document.getElementsByClassName("tablinks");

for (i = 0; i < tablinks.length; i++) {{
    tablinks[i].className =
    tablinks[i].className.replace(" active", "");
}}

document.getElementById(tabName).style.display = "block";

evt.currentTarget.className += " active";

}}

</script>

</head>

<body>

<div class="header">
<h1>채용 KPI 이상감지 대시보드</h1>
</div>

<div class="container">

<div class="cards">

<div class="card">
<h2>분석 월 수</h2>
<p>{total_months}</p>
</div>

<div class="card">
<h2>Z-score 이상월</h2>
<p>{z_months}</p>
</div>

<div class="card">
<h2>Isolation Forest</h2>
<p>{if_months}</p>
</div>

<div class="card">
<h2>중복 탐지</h2>
<p>{both_months}</p>
</div>

</div>

<div class="tab">

<button class="tablinks"
onclick="openTab(event,'kpi')">
KPI 이상감지
</button>

<button class="tablinks"
onclick="openTab(event,'iforest')">
Isolation Forest
</button>

<button class="tablinks"
onclick="openTab(event,'summary')">
요약 테이블
</button>

</div>

<div id="kpi" class="tabcontent">
{fig_applicant.to_html(full_html=False, include_plotlyjs='cdn')}
{fig_doc.to_html(full_html=False)}
{fig_final.to_html(full_html=False)}
{fig_ttf.to_html(full_html=False)}
</div>

<div id="iforest" class="tabcontent">
{fig_iforest.to_html(full_html=False)}
</div>

<div id="summary" class="tabcontent">
{summary.to_html(index=False)}
</div>

</div>

<script>
document.getElementsByClassName(
'tablinks'
)[0].click();
</script>

</body>
</html>
"""

with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:

    f.write(html)

print("=" * 60)
print("저장 완료")
print(output_file)
print("=" * 60)