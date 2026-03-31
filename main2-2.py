import pandas as pd
import matplotlib.pyplot as plt
import platform
import os
import warnings

warnings.filterwarnings('ignore')

# --- 1. 한글 폰트 및 시각화 설정 ---
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')  # 윈도우 맑은 고딕
plt.rcParams['axes.unicode_minus'] = False

# --- 2. 데이터 불러오기 ---
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#2\2_PAproject_2_3_EDA.csv"

print("데이터를 불러오고 전처리를 시작합니다...")
try:
    # 한글 데이터가 포함되어 있을 수 있으므로 cp949 인코딩 사용
    df = pd.read_csv(file_path, encoding='cp949')

    # --- 3. 날짜 데이터 전처리 ---
    # Hire_Date와 Termination_Date를 datetime 형식으로 변환 (에러 발생 시 빈칸 처리)
    df['Hire_Date'] = pd.to_datetime(df['Hire_Date'], errors='coerce')
    df['Termination_Date'] = pd.to_datetime(df['Termination_Date'], errors='coerce')

    # --- 4. 월별 퇴사율(Turnover Rate) 계산 로직 ---
    # 가장 빠른 입사월부터 가장 늦은 퇴사월까지의 기간 생성
    start_month = df['Hire_Date'].min()
    end_month = df['Termination_Date'].max()

    # 데이터에 날짜가 정상적으로 존재하는 경우만 실행
    if pd.notnull(start_month) and pd.notnull(end_month):
        months = pd.period_range(start=start_month, end=end_month, freq='M')

        month_labels = []
        turnover_rates = []

        for month in months:
            month_start = month.start_time
            month_end = month.end_time

            # 1) 해당 월의 활성 근무자(Active Employees) 수 계산
            # 입사일이 해당 월 마지막 날 이전이고, (퇴사하지 않았거나 OR 퇴사일이 해당 월 첫째 날 이후인 사람)
            active_condition = (df['Hire_Date'] <= month_end) & \
                               (df['Termination_Date'].isna() | (df['Termination_Date'] >= month_start))
            active_count = len(df[active_condition])

            # 2) 해당 월의 실제 퇴사자(Terminated Employees) 수 계산
            term_condition = (df['Termination_Date'] >= month_start) & (df['Termination_Date'] <= month_end)
            terminated_count = len(df[term_condition])

            # 3) 퇴사율 계산 (%)
            if active_count > 0:
                rate = (terminated_count / active_count) * 100
            else:
                rate = 0.0

            month_labels.append(month.strftime('%Y-%m'))
            turnover_rates.append(rate)

        # 분석용 데이터프레임 생성
        rate_df = pd.DataFrame({'Month': month_labels, 'Turnover_Rate': turnover_rates})

        # 분석 의미를 높이기 위해 최근 2년(24개월) 등 특정 기간만 필터링할 수도 있으나, 여기서는 전체를 그립니다.
        # 데이터가 너무 길 경우 가독성을 위해 최근 36개월만 추출 (선택 사항)
        if len(rate_df) > 36:
            rate_df = rate_df.tail(36)

        # --- 5. 시각화 진행 (2개의 그래프를 위아래로 배치) ---
        fig, axes = plt.subplots(2, 1, figsize=(12, 12))

        # [그래프 1] 월별 퇴사율 선 그래프 (Line Chart)
        axes[0].plot(rate_df['Month'], rate_df['Turnover_Rate'], marker='o', color='crimson', linewidth=2, markersize=6)
        axes[0].set_title('월별 퇴사율(Turnover Rate) 변동 추이', fontsize=16, fontweight='bold', pad=15)
        axes[0].set_ylabel('퇴사율 (%)', fontsize=12)
        axes[0].tick_params(axis='x', rotation=45)  # x축 날짜 글씨가 겹치지 않게 45도 회전
        axes[0].grid(True, linestyle='--', alpha=0.6)

        # [그래프 2] 자발적 vs 비자발적 퇴사 비중 원 그래프 (Pie Chart)
        # Status 컬럼에서 퇴사자 데이터만 필터링 (결측치 제외)
        term_status = df[df['Status'].isin(['Voluntary', 'Involuntary'])]['Status'].value_counts()

        if not term_status.empty:
            # 색상 및 스타일 설정
            colors = ['#ff9999', '#66b3ff']
            explode = (0.05, 0)  # 첫 번째 조각을 살짝 떼어내서 강조

            axes[1].pie(term_status, labels=term_status.index, autopct='%1.1f%%', startangle=90,
                        colors=colors, explode=explode, shadow=True, textprops={'fontsize': 14})
            axes[1].set_title('퇴사 사유 비중: 자발적(Voluntary) vs 비자발적(Involuntary)', fontsize=16, fontweight='bold', pad=15)
        else:
            axes[1].text(0.5, 0.5, 'Status 컬럼에 Voluntary/Involuntary 데이터가 없습니다.',
                         horizontalalignment='center', verticalalignment='center', fontsize=12)
            axes[1].axis('off')

        plt.tight_layout()
        print("🎉 EDA 시각화가 완료되었습니다. 팝업된 그래프 창을 확인해 주세요!")
        plt.show()

    else:
        print("날짜 데이터(Hire_Date, Termination_Date)에 유효한 값이 부족하여 퇴사율을 계산할 수 없습니다.")

except FileNotFoundError:
    print(f"오류: 지정된 경로에서 파일을 찾을 수 없습니다.\n경로: {file_path}")
except Exception as e:
    print(f"데이터 처리 중 오류가 발생했습니다: {e}")