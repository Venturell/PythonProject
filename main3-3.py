import pandas as pd
import matplotlib.pyplot as plt
import platform

# --- 4. 한글 폰트 및 마이너스 기호 깨짐 방지 설정 ---
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# 1. 파일 경로 설정 및 데이터 불러오기 (cp949 인코딩 유지)
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3\3_PAproject_3_3_NPS.csv"

print("데이터를 불러오고 분석을 시작합니다...")
# 지난번의 DtypeWarning을 방지하기 위해 low_memory=False 옵션을 사용합니다.
df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

try:
    # 2. 사업장가입상태코드가 2(탈퇴/폐업)인 데이터만 필터링
    df_closed = df[df['사업장가입상태코드'] == 2].copy()

    # 3. '탈퇴일자' 변수를 파이썬이 계산할 수 있는 날짜 형식(datetime)으로 변환
    # errors='coerce'를 넣으면 날짜 형식이 잘못된 데이터는 무시(NaT)하여 에러를 방지합니다.
    df_closed['탈퇴일자'] = pd.to_datetime(df_closed['탈퇴일자'], errors='coerce')

    # 탈퇴일자에서 연도가 2025년인 데이터만 한 번 더 필터링
    df_2025_closed = df_closed[df_closed['탈퇴일자'].dt.year == 2025].copy()

    if df_2025_closed.empty:
        print("2025년에 탈퇴(폐업)한 기업 데이터가 존재하지 않습니다.")
    else:
        # 탈퇴일자에서 '월(month)'만 추출하여 새로운 칼럼 생성
        df_2025_closed['탈퇴월'] = df_2025_closed['탈퇴일자'].dt.month

        # 월별로 폐업한 기업이 몇 개인지 숫자를 세고(value_counts), 1월부터 순서대로 정렬(sort_index)
        monthly_counts = df_2025_closed['탈퇴월'].value_counts().sort_index()

        # --- 그래프 (히스토그램 형태) 그리기 ---
        plt.figure(figsize=(10, 6))

        # 월별 분포를 보여줄 때는 막대(bar) 그래프를 히스토그램처럼 사용하는 것이 가장 깔끔합니다.
        bars = plt.bar(monthly_counts.index, monthly_counts.values, color='salmon', edgecolor='black')

        plt.title('2025년 월별 탈퇴(폐업) 기업 수 현황', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('월 (Month)', fontsize=12)
        plt.ylabel('폐업 기업 수 (개)', fontsize=12)

        # x축 눈금을 1월부터 12월까지 빠짐없이 표시되도록 강제 설정
        plt.xticks(range(1, 13), [f'{i}월' for i in range(1, 13)])

        # 각 막대 위에 정확한 건수를 텍스트로 달아줍니다.
        for bar in bars:
            yval = bar.get_height()
            # 높이가 0이 아닐 때만 글씨를 씁니다.
            if yval > 0:
                plt.text(bar.get_x() + bar.get_width() / 2, yval + (yval * 0.01),
                         f'{int(yval):,}건', ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        print("🎉 월별 폐업 현황 분석 완료! 그래프 창이 열립니다.")
        plt.show()

except KeyError as e:
    print(f"데이터에 해당 변수명이 존재하지 않습니다. 오탈자를 확인해 주세요: {e}")
except Exception as e:
    print(f"분석 중 오류가 발생했습니다: {e}")