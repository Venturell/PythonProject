import pandas as pd
import ruptures as rpt
import plotly.graph_objects as go
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. 파일 경로 및 데이터 로드
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#11\11_PAproject_11_1_recruit.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "changepoint_result.html")

print("데이터를 불러오고 전처리를 진행합니다...")

# timeseries 시트 로드 및 날짜 변환
df_ts = pd.read_excel(file_path, sheet_name='timeseries')
df_ts['date'] = pd.to_datetime(df_ts['date'])

# 전체 합계 기준으로 집계 및 정렬
df_total = df_ts.groupby('date')['posting_count'].sum().reset_index()
df_total = df_total.sort_values('date').reset_index(drop=True)

# ==========================================
# 2. 변곡점 탐지 (Change Point Detection)
# ==========================================
print("PELT 알고리즘으로 시계열 변곡점을 탐지 중입니다...")

# 분석할 시그널(데이터)을 numpy 배열로 변환
signal = df_total['posting_count'].values

# PELT 알고리즘 적용 (구간별 평균 변화 감지)
algo = rpt.Pelt(model="l2").fit(signal)

# penalty 값 설정 (15 정도면 큼직한 변곡점 위주로 탐지합니다)
penalty_value = 15
result = algo.predict(pen=penalty_value)

print(f"-> 총 {len(result) - 1}개의 변곡점이 발견되었습니다!")

# ==========================================
# 3. 인터랙티브 시각화 (Plotly)
# ==========================================
print("탐지된 구간을 시각화하여 HTML로 렌더링합니다...")

fig = go.Figure()

# 1) 원본 데이터 라인 차트
fig.add_trace(go.Scatter(
    x=df_total['date'],
    y=df_total['posting_count'],
    mode='lines+markers',
    name='월별 총 공고수',
    line=dict(color='gray', width=2),
    marker=dict(size=4)
))

# 구간별 배경색을 위한 컬러 팔레트
colors = ['rgba(31, 119, 180, 0.15)', 'rgba(255, 127, 14, 0.15)',
          'rgba(44, 160, 44, 0.15)', 'rgba(214, 39, 40, 0.15)',
          'rgba(148, 103, 189, 0.15)', 'rgba(140, 86, 75, 0.15)']

start_idx = 0

# 2) 탐지된 변곡점(result)을 순회하며 구간별 평균선, 배경색, 수직선 그리기
for i, cp in enumerate(result):
    segment_data = df_total.iloc[start_idx:cp]
    segment_mean = segment_data['posting_count'].mean()

    start_date = df_total['date'].iloc[start_idx]

    if cp < len(df_total):
        end_date = df_total['date'].iloc[cp]
    else:
        end_date = df_total['date'].iloc[-1]

    color_idx = i % len(colors)

    # [1] 구간별 평균선 (점선)
    fig.add_trace(go.Scatter(
        x=[start_date, end_date],
        y=[segment_mean, segment_mean],
        mode='lines',
        name=f'국면 {i + 1} 평균 ({int(segment_mean):,}건)',
        line=dict(color=colors[color_idx].replace('0.15', '1.0'), width=3, dash='dash')
    ))

    # [2] 구간별 배경색 지정
    fig.add_vrect(
        x0=start_date, x1=end_date,
        fillcolor=colors[color_idx],
        opacity=1,
        layer="below", line_width=0,
    )

    # 💡 [핵심 에러 해결 방안]
    # 에러 덩어리인 add_vline을 버리고, add_shape와 add_annotation으로 분리하여 직접 그립니다.
    if cp < len(df_total):
        # 수직선(Line) 그리기
        fig.add_shape(
            type="line",
            x0=end_date, y0=0, x1=end_date, y1=1,
            yref="paper",  # y축을 데이터가 아닌 0~1 비율(화면 전체 높이)로 설정
            line=dict(color="#d62728", width=2, dash="solid")
        )
        # 글씨(Annotation) 그리기
        fig.add_annotation(
            x=end_date, y=1, yref="paper",
            text=f"변곡점: {end_date.strftime('%Y-%m')}",
            showarrow=False,
            xanchor="left", yanchor="bottom",
            font=dict(color="#d62728", size=12)
        )

    start_idx = cp

# 레이아웃 세부 설정
fig.update_layout(
    title_text="📊 채용 시장 수요 변곡점 탐지 (Change Point Detection - PELT)",
    title_font_size=20,
    xaxis_title="연월",
    yaxis_title="공고 수 (건)",
    hovermode="x unified",
    plot_bgcolor='#ffffff',
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0')
fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f0f0f0')

# ==========================================
# 4. 결과 저장
# ==========================================
fig.write_html(output_path, include_plotlyjs='cdn')

print("\n" + "=" * 60)
print("✅ Plotly 버그 완벽 우회! PELT 변곡점 탐지 및 시각화가 완료되었습니다.")
print(f"📁 저장 경로: {output_path}")
print("=" * 60)