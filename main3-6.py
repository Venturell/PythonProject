import pandas as pd
import matplotlib.pyplot as plt
import platform

# --- 5. 한글 폰트 및 마이너스 기호 깨짐 방지 설정 ---
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# 1. 파일 경로 설정 및 데이터 불러오기 (cp949 인코딩)
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3\3_PAproject_3_3_NPS.csv"

print("데이터를 불러오고 분석을 시작합니다...")
# DtypeWarning을 방지하기 위해 low_memory=False 옵션 유지
df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

try:
    # 2. 사업장가입상태코드가 1(정상)인 기업 필터링
    df_active = df[df['사업장가입상태코드'] == 1].copy()

    # 4. 비교할 대상 기업 리스트 설정 및 데이터 추출
    target_companies = ["에스케이하이닉스 주식회사", "삼성전자(주)", "한미반도체(주)", "에스케이실트론주식회사"]
    df_targets = df_active[df_active['사업장명'].isin(target_companies)].copy()

    if df_targets.empty:
        print("입력하신 경쟁사 데이터가 존재하지 않습니다. 기업명을 확인해 주세요.")
    else:
        # 3. 인당금액 및 연봉 계산
        df_targets['인당금액'] = df_targets['당월고지금액'] / df_targets['가입자수']
        df_targets['연봉(원)'] = (df_targets['인당금액'] / 0.095) * 12

        # 가독성을 위해 만원 단위로 변환
        df_targets['연봉(만원)'] = df_targets['연봉(원)'] / 10000

        # 기업별로 여러 사업장이 있을 경우를 대비해 기업명 기준으로 연봉 평균 산출
        df_plot = df_targets.groupby('사업장명')['연봉(만원)'].mean().reset_index()

        # 연봉이 높은 순서대로 보기 좋게 정렬
        df_plot = df_plot.sort_values(by='연봉(만원)', ascending=False)

        # 텍스트 결과 출력
        print("\n=== 주요 경쟁사 연봉 벤치마킹 결과 ===")
        # 소수점 아래를 버리고 깔끔하게 정수로 출력
        df_plot['연봉(만원)'] = df_plot['연봉(만원)'].astype(int)
        print(df_plot.to_string(index=False))
        print("=======================================\n")

        # --- 4 & 5. 그래프 (막대그래프) 그리기 ---
        plt.figure(figsize=(10, 6))

        # 에스케이하이닉스만 눈에 띄게 다른 색상으로 칠하기 위한 색상 리스트 만들기
        colors = ['cornflowerblue' if name == '에스케이하이닉스 주식회사' else 'lightgray' for name in df_plot['사업장명']]

        bars = plt.bar(df_plot['사업장명'], df_plot['연봉(만원)'], color=colors, edgecolor='black', width=0.6)

        plt.title('경쟁업체 간 추정 평균 연봉 비교', fontsize=16, fontweight='bold', pad=20)
        plt.ylabel('추정 연봉 (만원)', fontsize=12)

        # x축 기업명 기울이기
        plt.xticks(rotation=15, fontsize=11)

        # 각 막대 위에 연봉 값 표시
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2, yval + (yval * 0.01),
                     f'{int(yval):,}만원', ha='center', va='bottom', fontsize=12, fontweight='bold')

        # 텍스트가 잘리지 않도록 y축 여백 확보
        plt.ylim(0, df_plot['연봉(만원)'].max() * 1.15)

        plt.tight_layout()
        print("🎉 경쟁사 비교 분석 완료! 그래프 창이 열립니다.")
        plt.show()

except KeyError as e:
    print(f"데이터에 해당 변수명이 존재하지 않습니다. 오탈자를 확인해 주세요: {e}")
except Exception as e:
    print(f"분석 중 오류가 발생했습니다: {e}")