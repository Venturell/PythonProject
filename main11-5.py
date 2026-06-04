import os
import pandas as pd
import plotly.graph_objects as gr
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import STL


def perform_stl_analysis(file_path, output_html="stl_result.html"):
    # 1. 데이터 로드 및 전처리
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"엑셀 파일을 찾을 수 없습니다: {file_path}")

    print("데이터를 로드하는 중...")
    df = pd.read_excel(file_path, sheet_name='timeseries')

    # 날짜 형식 변환 및 정렬 (시계열 분석을 위해 필수)
    df['date'] = pd.to_datetime(df['date'])

    # 전체 직종의 합계를 구하여 월별 전체 공고수 시계열 생성
    df_total = df.groupby('date')['posting_count'].sum().sort_index()

    # 명시적으로 월별 주기(Monthly frequency) 설정
    df_total = df_total.asfreq('MS')

    # 혹시 모를 결측치가 있다면 선형 보간 처리
    if df_total.isnull().any():
        print("공백 날짜 또는 결측치가 발견되어 보간 처리를 진행합니다.")
        df_total = df_total.interpolate(method='linear')

    # 2. STL 분해 적용
    print("STL 분해를 적용하는 중...")
    # period=12: 월별 데이터이므로 1년 주기(12개월) 설정
    # robust=True: 아웃라이어(이상치)의 영향을 줄임
    stl = STL(df_total, period=12, robust=True)
    res = stl.fit()

    # 3. Plotly 인터랙티브 서브플롯 차트 생성 (4단 구성)
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            "<b>1. 원본 데이터 (Observed)</b> - 월별 전체 채용 공고 수 합계",
            "<b>2. 장기 추세 (Trend)</b> - 경기 및 시장 구조적 변화",
            "<b>3. 계절성 패턴 (Seasonal)</b> - 연중 정기적 반복 패턴",
            "<b>4. 잔차/불규칙 요인 (Residual)</b> - 특수 요인 및 노이즈"
        )
    )

    # 1) Observed (원본)
    fig.add_trace(
        gr.Scatter(x=df_total.index, y=res.observed, mode='lines+markers', name='Observed',
                   line=dict(color='#1f4068', width=2)),
        row=1, col=1
    )
    # 2) Trend (추세)
    fig.add_trace(
        gr.Scatter(x=df_total.index, y=res.trend, mode='lines', name='Trend', line=dict(color='#e43f5a', width=2.5)),
        row=2, col=1
    )
    # 3) Seasonal (계절성)
    fig.add_trace(
        gr.Scatter(x=df_total.index, y=res.seasonal, mode='lines+markers', name='Seasonal',
                   line=dict(color='#10b981', width=2)),
        row=3, col=1
    )
    # 4) Residual (잔차)
    fig.add_trace(
        gr.Bar(x=df_total.index, y=res.resid, name='Residual', marker=dict(color='#64748b')),
        row=4, col=1
    )

    # 차트 레이아웃 구성 개별 세팅
    fig.update_layout(
        title=dict(
            text="<b>채용공고 시계열 데이터 STL 분해 결과 리포트</b>",
            x=0.5, y=0.96, font=dict(size=22)
        ),
        height=900,
        showlegend=False,
        hovermode="x unified",  # 마우스를 올리면 같은 시점의 모든 플롯 값이 한 번에 노출됨
        template="plotly_white"
    )

    # 축 제목 세팅
    fig.update_yaxes(title_text="공고 수 (건)", row=1, col=1)
    fig.update_yaxes(title_text="추세 수치", row=2, col=1)
    fig.update_yaxes(title_text="계절성 편차", row=3, col=1)
    fig.update_yaxes(title_text="잔차 편차", row=4, col=1)
    fig.update_xaxes(title_text="연월 (Date)", row=4, col=1)

    # 4. 결과 HTML 파일 저장 (TypeError 오류 유발 인자 제거)
    print(f"인터랙티브 리포트를 저장하는 중: {output_html}")
    fig.write_html(output_html, include_plotlyjs='cdn')
    print("STL 분해 시각화 페이지 생성 완료!")


if __name__ == "__main__":
    EXCEL_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#11\11_PAproject_11_2_pipeline.xlsx"
    perform_stl_analysis(EXCEL_PATH)