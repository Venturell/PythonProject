import pandas as pd
from statsmodels.tsa.seasonal import STL
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. 파일 경로 및 환경 설정
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#11\11_PAproject_11_1_recruit.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "stl_result.html")

print("데이터를 불러오고 전처리를 진행합니다...")

# ==========================================
# 2. 데이터 로드 및 시계열 전처리
# ==========================================
# timeseries 시트 로드
df_ts = pd.read_excel(file_path, sheet_name='timeseries')

# 'date' 컬럼을 Datetime 객체로 강제 변환
df_ts['date'] = pd.to_datetime(df_ts['date'])

# 전체 합계 기준으로 집계 (직종 구분 없이 월별 총 공고 수)
df_total = df_ts.groupby('date')['posting_count'].sum().reset_index()

# 날짜 순으로 정렬 후, date를 인덱스로 설정 (statsmodels 시계열 분석의 필수 요건)
df_total = df_total.sort_values('date').set_index('date')

# ==========================================
# 3. STL 분해 (Seasonal and Trend decomposition)
# ==========================================
print("STL 분해 모델을 적용 중입니다...")

# 월별 데이터이므로 period=12를 적용합니다.
# seasonal 파라미터는 계절성을 평활화하는 윈도우 크기로, 일반적으로 홀수를 사용합니다.
stl = STL(df_total['posting_count'], period=12, seasonal=13)
res = stl.fit()

# ==========================================
# 4. Plotly 인터랙티브 서브플롯 생성
# ==========================================
print("분석 결과를 시각화하고 HTML로 렌더링합니다...")

# 4행 1열의 차트 틀 생성 (X축은 공유)
fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    subplot_titles=(
        '1. 원본 데이터 (Original Time Series)',
        '2. 장기적 추세 (Trend)',
        '3. 반복되는 계절성 (Seasonal)',
        '4. 설명되지 않는 잔차/이벤트 (Residual)'
    )
)

# 1) 원본 데이터
fig.add_trace(go.Scatter(
    x=df_total.index, y=df_total['posting_count'],
    mode='lines+markers', name='Original', line=dict(color='#1f77b4', width=2)
), row=1, col=1)

# 2) 추세 (Trend)
fig.add_trace(go.Scatter(
    x=res.trend.index, y=res.trend,
    mode='lines', name='Trend', line=dict(color='#ff7f0e', width=3)
), row=2, col=1)

# 3) 계절성 (Seasonal)
fig.add_trace(go.Scatter(
    x=res.seasonal.index, y=res.seasonal,
    mode='lines', name='Seasonal', line=dict(color='#2ca02c', width=2)
), row=3, col=1)

# 4) 잔차 (Residual)
fig.add_trace(go.Scatter(
    x=res.resid.index, y=res.resid,
    mode='markers', name='Residual', marker=dict(color='#d62728', size=5)
), row=4, col=1)

# 잔차 차트에 0 기준선 추가
fig.add_hline(y=0, line_dash="dash", line_color="gray", row=4, col=1)

# 전체 레이아웃 세부 설정
fig.update_layout(
    height=900,
    title_text="📊 채용 공고 시장 전체 시계열 STL 분해 결과",
    title_font_size=20,
    hovermode="x unified",
    showlegend=False,
    plot_bgcolor='#f8f9fa',
    paper_bgcolor='#ffffff'
)

# Y축 타이틀 추가
fig.update_yaxes(title_text="공고 수", row=1, col=1)
fig.update_yaxes(title_text="추세 수준", row=2, col=1)
fig.update_yaxes(title_text="계절 편차", row=3, col=1)
fig.update_yaxes(title_text="오차", row=4, col=1)

# ==========================================
# 5. HTML 저장
# ==========================================
# 별도의 외부 스크립트 종속 없이 단독 실행 가능한 HTML 생성
fig.write_html(output_path, include_plotlyjs='cdn')

print("\n" + "=" * 60)
print("✅ STL 분해 및 시각화가 완료되었습니다!")
print(f"📁 저장 경로: {output_path}")
print("💡 해당 HTML 파일을 열어보시면 그래프 위를 마우스로 드래그하여 확대하거나 세부 수치를 확인할 수 있습니다.")
print("=" * 60)