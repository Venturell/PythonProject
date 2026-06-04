import pandas as pd
import numpy as np

from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import (
    accuracy_score,
    roc_auc_score
)

import plotly.express as px
import plotly.graph_objects as go

# =====================================================
# 파일 경로
# =====================================================

file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#11\11_PAproject_11_2_pipeline.xlsx"

output_file = (
    Path(file_path).parent
    / "profiling_result.html"
)

# =====================================================
# 데이터 로드
# =====================================================

df = pd.read_excel(
    file_path,
    sheet_name="result"
)

# =====================================================
# 타겟 생성
# =====================================================

df["target"] = (
    df["final_result"]
    .astype(str)
    .eq("합격")
    .astype(int)
)

# =====================================================
# 결측 제거
# =====================================================

features = [
    "age",
    "career_years",
    "score_resume",
    "score_interview1",
    "score_interview2"
]

df = df.dropna(
    subset=features + ["target"]
)

# =====================================================
# EDA
# =====================================================

fig_age = px.box(
    df,
    x="final_result",
    y="age",
    color="final_result",
    title="Age Distribution"
)

fig_career = px.box(
    df,
    x="final_result",
    y="career_years",
    color="final_result",
    title="Career Years Distribution"
)

fig_resume = px.box(
    df,
    x="final_result",
    y="score_resume",
    color="final_result",
    title="Resume Score Distribution"
)

fig_interview1 = px.box(
    df,
    x="final_result",
    y="score_interview1",
    color="final_result",
    title="Interview1 Score Distribution"
)

fig_interview2 = px.box(
    df,
    x="final_result",
    y="score_interview2",
    color="final_result",
    title="Interview2 Score Distribution"
)

# =====================================================
# 직종 × 학력 합격률
# =====================================================

heat = (
    df.groupby(
        ["job_category", "education"]
    )["target"]
    .mean()
    .reset_index()
)

fig_heatmap = px.density_heatmap(
    heat,
    x="education",
    y="job_category",
    z="target",
    text_auto=".2f",
    title="Hire Rate Heatmap"
)

# =====================================================
# 모델링
# =====================================================

X = df[features]

y = df["target"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# =====================================================
# Logistic Regression
# =====================================================

log_model = LogisticRegression(
    max_iter=5000
)

log_model.fit(
    X_train,
    y_train
)

log_pred = log_model.predict(
    X_test
)

log_prob = log_model.predict_proba(
    X_test
)[:, 1]

log_acc = accuracy_score(
    y_test,
    log_pred
)

log_auc = roc_auc_score(
    y_test,
    log_prob
)

coef_df = pd.DataFrame({
    "Feature": features,
    "Coefficient": log_model.coef_[0]
})

coef_df = coef_df.sort_values(
    "Coefficient"
)

fig_coef = px.bar(
    coef_df,
    x="Coefficient",
    y="Feature",
    orientation="h",
    title="Logistic Regression Coefficients"
)

# =====================================================
# Random Forest
# =====================================================

rf_model = RandomForestClassifier(
    n_estimators=300,
    random_state=42
)

rf_model.fit(
    X_train,
    y_train
)

rf_pred = rf_model.predict(
    X_test
)

rf_prob = rf_model.predict_proba(
    X_test
)[:, 1]

rf_acc = accuracy_score(
    y_test,
    rf_pred
)

rf_auc = roc_auc_score(
    y_test,
    rf_prob
)

importance_df = pd.DataFrame({
    "Feature": features,
    "Importance": rf_model.feature_importances_
})

importance_df = importance_df.sort_values(
    "Importance"
)

fig_importance = px.bar(
    importance_df,
    x="Importance",
    y="Feature",
    orientation="h",
    title="Random Forest Feature Importance"
)

# =====================================================
# 성능 비교
# =====================================================

performance = pd.DataFrame({
    "Model": [
        "Logistic Regression",
        "Random Forest"
    ],
    "Accuracy": [
        round(log_acc, 4),
        round(rf_acc, 4)
    ],
    "AUC": [
        round(log_auc, 4),
        round(rf_auc, 4)
    ]
})

# =====================================================
# KPI 카드
# =====================================================

total_candidate = len(df)

hire_count = df["target"].sum()

hire_rate = (
    hire_count /
    total_candidate
)

# =====================================================
# HTML
# =====================================================

html = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="utf-8">

<title>Candidate Profiling Dashboard</title>

<style>

body {{
    margin:0;
    font-family:Arial;
    background:#f4f6f9;
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
    flex:1;
    background:white;
    padding:20px;
    border-radius:12px;
    box-shadow:0 2px 8px rgba(0,0,0,0.15);
    text-align:center;
}}

.tab {{
    overflow:hidden;
    background:white;
    border-radius:12px;
}}

.tab button {{
    float:left;
    border:none;
    background:inherit;
    padding:14px 20px;
    cursor:pointer;
}}

.tabcontent {{
    display:none;
    background:white;
    padding:20px;
    margin-top:10px;
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

function openTab(evt, name) {{

let i;

let tabcontent =
document.getElementsByClassName("tabcontent");

for(i=0;i<tabcontent.length;i++){{
tabcontent[i].style.display="none";
}}

let tablinks =
document.getElementsByClassName("tablinks");

for(i=0;i<tablinks.length;i++){{
tablinks[i].className=
tablinks[i].className.replace(
" active",""
);
}}

document.getElementById(name).style.display="block";

evt.currentTarget.className+=" active";

}}

</script>

</head>

<body>

<div class="header">
<h1>합격자 프로파일링 및 예측 대시보드</h1>
</div>

<div class="container">

<div class="cards">

<div class="card">
<h3>지원자 수</h3>
<h1>{total_candidate:,}</h1>
</div>

<div class="card">
<h3>합격자 수</h3>
<h1>{hire_count:,}</h1>
</div>

<div class="card">
<h3>합격률</h3>
<h1>{hire_rate:.1%}</h1>
</div>

<div class="card">
<h3>분석 변수 수</h3>
<h1>{len(features)}</h1>
</div>

</div>

<div class="tab">

<button class="tablinks"
onclick="openTab(event,'eda')">
EDA
</button>

<button class="tablinks"
onclick="openTab(event,'logistic')">
Logistic Regression
</button>

<button class="tablinks"
onclick="openTab(event,'rf')">
Random Forest
</button>

<button class="tablinks"
onclick="openTab(event,'compare')">
성능 비교
</button>

</div>

<div id="eda" class="tabcontent">

{fig_age.to_html(full_html=False, include_plotlyjs='cdn')}
{fig_career.to_html(full_html=False)}
{fig_resume.to_html(full_html=False)}
{fig_interview1.to_html(full_html=False)}
{fig_interview2.to_html(full_html=False)}
{fig_heatmap.to_html(full_html=False)}

</div>

<div id="logistic" class="tabcontent">

<h2>Accuracy : {log_acc:.4f}</h2>
<h2>AUC : {log_auc:.4f}</h2>

{fig_coef.to_html(full_html=False)}

</div>

<div id="rf" class="tabcontent">

<h2>Accuracy : {rf_acc:.4f}</h2>
<h2>AUC : {rf_auc:.4f}</h2>

{fig_importance.to_html(full_html=False)}

</div>

<div id="compare" class="tabcontent">

{performance.to_html(index=False)}

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
print("분석 완료")
print(f"저장 위치: {output_file}")
print("=" * 60)