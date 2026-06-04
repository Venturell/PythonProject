import pandas as pd
import numpy as np

from prophet import Prophet
from pmdarima import auto_arima

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error
)

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# =====================================================
# 1. 데이터 로드
# =====================================================

file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#11\11_PAproject_11_1_recruit.xlsx"

df = pd.read_excel(
    file_path,
    sheet_name="timeseries"
)

# =====================================================
# 2. 날짜 생성
# =====================================================

df["date"] = pd.to_datetime(df["date"])

# =====================================================
# 3. 전체 월별 채용수요 집계
# =====================================================

total_ts = (
    df.groupby("date")["posting_count"]
    .sum()
    .reset_index()
)

total_ts = total_ts.sort_values("date")

# =====================================================
# 4. Train / Test
# =====================================================

test_size = 12

train = total_ts.iloc[:-test_size]
test = total_ts.iloc[-test_size:]

# =====================================================
# 5. AUTO ARIMA
# =====================================================

arima_model = auto_arima(
    train["posting_count"],
    seasonal=True,
    m=12,
    trace=True,
    suppress_warnings=True,
    stepwise=True
)

# 테스트 예측
arima_test_pred = arima_model.predict(
    n_periods=len(test)
)

# 미래 12개월 예측
arima_future_fc, arima_future_ci = arima_model.predict(
    n_periods=12,
    return_conf_int=True
)

future_dates = pd.date_range(
    total_ts["date"].max() + pd.offsets.MonthBegin(1),
    periods=12,
    freq="MS"
)

# =====================================================
# 6. Prophet
# =====================================================

prophet_df = train.rename(
    columns={
        "date": "ds",
        "posting_count": "y"
    }
)

prophet_model = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=False,
    daily_seasonality=False
)

prophet_model.fit(prophet_df)

# 테스트 예측

future_test = prophet_model.make_future_dataframe(
    periods=len(test),
    freq="MS"
)

forecast_test = prophet_model.predict(
    future_test
)

prophet_test_pred = (
    forecast_test["yhat"]
    .tail(len(test))
    .values
)

# 미래 12개월 예측

future_12 = prophet_model.make_future_dataframe(
    periods=12,
    freq="MS"
)

forecast_12 = prophet_model.predict(
    future_12
)

future_prophet = forecast_12.tail(12)

# =====================================================
# 7. 성능 비교
# =====================================================

rmse_arima = np.sqrt(
    mean_squared_error(
        test["posting_count"],
        arima_test_pred
    )
)

mae_arima = mean_absolute_error(
    test["posting_count"],
    arima_test_pred
)

rmse_prophet = np.sqrt(
    mean_squared_error(
        test["posting_count"],
        prophet_test_pred
    )
)

mae_prophet = mean_absolute_error(
    test["posting_count"],
    prophet_test_pred
)

performance = pd.DataFrame({
    "Model": ["ARIMA", "Prophet"],
    "RMSE": [rmse_arima, rmse_prophet],
    "MAE": [mae_arima, mae_prophet]
})

# =====================================================
# 8. ARIMA 그래프
# =====================================================

fig_arima = go.Figure()

fig_arima.add_trace(
    go.Scatter(
        x=total_ts["date"],
        y=total_ts["posting_count"],
        name="Actual"
    )
)

fig_arima.add_trace(
    go.Scatter(
        x=future_dates,
        y=arima_future_fc,
        name="ARIMA Forecast"
    )
)

fig_arima.add_trace(
    go.Scatter(
        x=np.concatenate([
            future_dates,
            future_dates[::-1]
        ]),
        y=np.concatenate([
            arima_future_ci[:,0],
            arima_future_ci[:,1][::-1]
        ]),
        fill="toself",
        name="95% CI",
        line=dict(color="rgba(0,0,0,0)")
    )
)

fig_arima.update_layout(
    title="ARIMA Forecast"
)

# =====================================================
# 9. Prophet 그래프
# =====================================================

fig_prophet = go.Figure()

fig_prophet.add_trace(
    go.Scatter(
        x=total_ts["date"],
        y=total_ts["posting_count"],
        name="Actual"
    )
)

fig_prophet.add_trace(
    go.Scatter(
        x=forecast_12["ds"],
        y=forecast_12["yhat"],
        name="Prophet Forecast"
    )
)

fig_prophet.add_trace(
    go.Scatter(
        x=np.concatenate([
            forecast_12["ds"],
            forecast_12["ds"][::-1]
        ]),
        y=np.concatenate([
            forecast_12["yhat_lower"],
            forecast_12["yhat_upper"][::-1]
        ]),
        fill="toself",
        name="95% CI"
    )
)

fig_prophet.update_layout(
    title="Prophet Forecast"
)

# =====================================================
# 10. 모델 비교 그래프
# =====================================================

fig_compare = go.Figure()

fig_compare.add_trace(
    go.Scatter(
        x=future_dates,
        y=arima_future_fc,
        name="ARIMA"
    )
)

fig_compare.add_trace(
    go.Scatter(
        x=future_prophet["ds"],
        y=future_prophet["yhat"],
        name="Prophet"
    )
)

fig_compare.update_layout(
    title="ARIMA vs Prophet Forecast"
)

# =====================================================
# 11. Prophet Trend
# =====================================================

fig_trend = px.line(
    forecast_12,
    x="ds",
    y="trend",
    title="Prophet Trend Component"
)

# =====================================================
# 12. Prophet Seasonality
# =====================================================

if "yearly" in forecast_12.columns:

    fig_seasonality = px.line(
        forecast_12,
        x="ds",
        y="yearly",
        title="Prophet Yearly Seasonality"
    )

else:

    fig_seasonality = go.Figure()

# =====================================================
# 13. 직종별 Prophet 예측
# =====================================================

job_fig = go.Figure()

buttons = []

for idx, job in enumerate(sorted(df["job_category"].unique())):

    temp = (
        df[df["job_category"] == job]
        .groupby("date")["posting_count"]
        .sum()
        .reset_index()
    )

    if len(temp) < 24:
        continue

    job_df = temp.rename(
        columns={
            "date":"ds",
            "posting_count":"y"
        }
    )

    m = Prophet(
        yearly_seasonality=True
    )

    m.fit(job_df)

    future = m.make_future_dataframe(
        periods=12,
        freq="MS"
    )

    fc = m.predict(future)

    visible = (idx == 0)

    job_fig.add_trace(
        go.Scatter(
            x=fc["ds"],
            y=fc["yhat"],
            name=job,
            visible=visible
        )
    )

for i, job in enumerate(sorted(df["job_category"].unique())):

    buttons.append(
        dict(
            label=job,
            method="update",
            args=[
                {
                    "visible":[
                        j==i
                        for j in range(
                            len(sorted(df["job_category"].unique()))
                        )
                    ]
                }
            ]
        )
    )

job_fig.update_layout(
    title="Job Category Forecast",
    updatemenus=[
        dict(
            buttons=buttons
        )
    ]
)

# =====================================================
# 14. HTML 저장
# =====================================================

html = """
<html>
<head>
<meta charset="utf-8">
<title>Recruitment Forecast Dashboard</title>
</head>
<body>

<h1>Recruitment Demand Forecast Dashboard</h1>

<h2>Model Performance</h2>
"""

html += performance.to_html(index=False)

html += fig_arima.to_html(
    full_html=False,
    include_plotlyjs="cdn"
)

html += fig_prophet.to_html(
    full_html=False
)

html += fig_compare.to_html(
    full_html=False
)

html += fig_trend.to_html(
    full_html=False
)

html += fig_seasonality.to_html(
    full_html=False
)

html += job_fig.to_html(
    full_html=False
)

html += """
</body>
</html>
"""

with open(
    "forecast_result.html",
    "w",
    encoding="utf-8"
) as f:

    f.write(html)

print("=" * 60)
print("Forecast Dashboard 생성 완료")
print("forecast_result.html")
print("=" * 60)

print("\nModel Performance")
print(performance)