import pandas as pd
import plotly.express as px
from pathlib import Path

# =====================================================
# 1. 데이터 불러오기
# =====================================================

file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#11\11_PAproject_11_2_pipeline.xlsx"

df = pd.read_excel(
    file_path,
    sheet_name="pipeline"
)

# =====================================================
# 2. 합격자만 분석
# =====================================================

df = df[df["result"] == "합격"].copy()

# =====================================================
# 3. 데이터 정리
# =====================================================

df["time_to_fill"] = pd.to_numeric(
    df["time_to_fill"],
    errors="coerce"
)

df["apply_date"] = pd.to_datetime(
    df["apply_date"],
    errors="coerce"
)

df = df.dropna(
    subset=["time_to_fill", "apply_date"]
)

# =====================================================
# 4. 파생 변수 생성
# =====================================================

df["year"] = df["apply_date"].dt.year

df["month_label"] = (
    df["apply_date"]
    .dt.to_period("M")
    .astype(str)
)

# =====================================================
# 5. 기본 통계
# =====================================================

mean_ttf = df["time_to_fill"].mean()
median_ttf = df["time_to_fill"].median()

# =====================================================
# 6. 그래프 1
# 전체 분포
# =====================================================

fig_hist = px.histogram(
    df,
    x="time_to_fill",
    nbins=30,
    title="Time-to-Fill Distribution"
)

fig_hist.add_vline(
    x=mean_ttf,
    line_dash="dash",
    annotation_text=f"Mean = {mean_ttf:.1f}"
)

fig_hist.add_vline(
    x=median_ttf,
    line_dash="dot",
    annotation_text=f"Median = {median_ttf:.1f}"
)

# =====================================================
# 7. 그래프 2
# 직종별 Box Plot
# =====================================================

job_order = (
    df.groupby("job_category")["time_to_fill"]
    .median()
    .sort_values()
    .index
)

fig_box = px.box(
    df,
    x="job_category",
    y="time_to_fill",
    category_orders={
        "job_category": job_order
    },
    title="Time-to-Fill by Job Category"
)

# =====================================================
# 8. 그래프 3
# 월별 추이
# =====================================================

monthly = (
    df.groupby("month_label")["time_to_fill"]
    .mean()
    .reset_index()
    .sort_values("month_label")
)

fig_month = px.line(
    monthly,
    x="month_label",
    y="time_to_fill",
    markers=True,
    title="Monthly Average Time-to-Fill"
)

# =====================================================
# 9. 그래프 4
# 연도별 추이
# =====================================================

yearly = (
    df.groupby("year")["time_to_fill"]
    .mean()
    .reset_index()
)

fig_year = px.bar(
    yearly,
    x="year",
    y="time_to_fill",
    text_auto=".1f",
    title="Yearly Average Time-to-Fill"
)

# =====================================================
# 10. 그래프 5
# 직종 × 월 Heatmap
# =====================================================

heatmap_data = (
    df.pivot_table(
        index="job_category",
        columns="month_label",
        values="time_to_fill",
        aggfunc="mean"
    )
)

fig_heatmap = px.imshow(
    heatmap_data,
    aspect="auto",
    title="Average Time-to-Fill Heatmap"
)

# =====================================================
# 11. 그래프 6
# 직종별 평균 비교
# =====================================================

job_avg = (
    df.groupby("job_category")["time_to_fill"]
    .mean()
    .sort_values()
    .reset_index()
)

fig_job_avg = px.bar(
    job_avg,
    x="job_category",
    y="time_to_fill",
    text_auto=".1f",
    title="Average Time-to-Fill by Job Category"
)

# =====================================================
# 12. HTML 생성
# =====================================================

html_parts = []

html_parts.append("""
<html>
<head>
<meta charset="utf-8">
<title>Time-to-Fill Dashboard</title>
</head>
<body>
<h1>Time-to-Fill Analysis Dashboard</h1>
""")

html_parts.append(
    f"""
    <h2>Summary Statistics</h2>
    <ul>
        <li>Average Time-to-Fill: {mean_ttf:.2f} days</li>
        <li>Median Time-to-Fill: {median_ttf:.2f} days</li>
        <li>Total Hires: {len(df):,}</li>
    </ul>
    """
)

html_parts.append(
    fig_hist.to_html(
        full_html=False,
        include_plotlyjs="cdn"
    )
)

html_parts.append(
    fig_box.to_html(
        full_html=False
    )
)

html_parts.append(
    fig_month.to_html(
        full_html=False
    )
)

html_parts.append(
    fig_year.to_html(
        full_html=False
    )
)

html_parts.append(
    fig_heatmap.to_html(
        full_html=False
    )
)

html_parts.append(
    fig_job_avg.to_html(
        full_html=False
    )
)

html_parts.append("""
</body>
</html>
""")

# =====================================================
# 13. 저장
# =====================================================

output_file = "time_to_fill.html"

with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:
    f.write("".join(html_parts))

print("=" * 60)
print("분석 완료")
print(f"파일 저장: {Path(output_file).resolve()}")
print("=" * 60)

print(f"평균 Time-to-Fill : {mean_ttf:.2f}일")
print(f"중앙값 Time-to-Fill : {median_ttf:.2f}일")
print(f"합격자 수 : {len(df):,}명")