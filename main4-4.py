import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
import platform
import os

# --- 한글 폰트 깨짐 방지 설정 (Windows 기준 '맑은 고딕') ---
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# 1 & 6. 파일 경로 설정 및 데이터 불러오기 (cp949 인코딩 유지)
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3\3_PAproject_3_3_NPS.csv"

if not os.path.exists(file_path):
    print(f"오류: 지정된 경로에 파일을 찾을 수 없습니다.\n경로: {file_path}")
else:
    print("NPS 데이터를 불러오는 중입니다...")
    try:
        df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

        # 2. 필터링: 사업장가입상태코드 1(정상) & 가입자수 200명 이상 대기업
        print("데이터 필터링 및 전처리 중...")
        # 데이터 타입 안전하게 변환
        df['사업장가입상태코드'] = pd.to_numeric(df['사업장가입상태코드'], errors='coerce')
        df['가입자수'] = pd.to_numeric(df['가입자수'], errors='coerce')
        df['당월고지금액'] = pd.to_numeric(df['당월고지금액'], errors='coerce')

        df_filtered = df[(df['사업장가입상태코드'] == 1) & (df['가입자수'] >= 200)].copy()

        # 3. 연봉 추정 계산 (원 단위)
        # "인당금액" 은 "당월고지금액" 변수를 "가입자수" 로 나눈 값
        df_filtered['인당금액'] = df_filtered['당월고지금액'] / df_filtered['가입자수']
        # "연봉" 은 "인당금액" 을 0.095 로 나누고 12를 곱한 값
        df_filtered['연봉'] = (df_filtered['인당금액'] / 0.095) * 12

        # 4 & 5. 그래프 시각화를 위한 전처리 ('만원' 단위 변환)
        df_filtered['연봉(만원)'] = df_filtered['연봉'] / 10000

        # 분석에 사용할 변수들만 추출하고 결측치 제거
        data_for_ana = df_filtered[['가입자수', '연봉', '연봉(만원)']].dropna()

        if data_for_ana.empty:
            print("조건에 맞는 분석 가능한 데이터가 존재하지 않습니다.")
        else:
            # --- 4. 회귀분석 수행 (statsmodels OLS) ---
            print("가입자수가 연봉에 미치는 영향에 대한 상세 회귀분석을 수행합니다...\n")

            # 독립변수 (X): 가입자수, 종속변수 (y): 연봉 (원 단위, 상세 보고서용)
            X_log = data_for_ana['가입자수']
            y_log = data_for_ana['연봉']

            # 상수의(절편) 추가
            X_log = sm.add_constant(X_log)

            # OLS 모델 피팅
            model = sm.OLS(y_log, X_log)
            results = model.fit()

            # 상세 회귀분석 결과 보고서 출력
            print("="*80)
            print("### [회귀 분석 결과 보고서: 기업 규모 vs 연봉] ###")
            print("="*80)
            # 지난번처럼 상세한 표 형태의 summary를 출력합니다.
            print(results.summary())
            print("="*80 + "\n")

            # --- 5. 시각화 (산점도 및 회귀선 그래프 그리기) ---
            print("그래프 시각화를 시작합니다...")
            plt.figure(figsize=(12, 8))

            # Seaborn의 regplot을 사용하여 산점도와 회귀선을 동시에 그립니다.
            # x축: 가입자수, y축: 연봉(만원) - 시각화 가독성을 위해 만원 단위 사용
            sns.regplot(data=data_for_ana, x='가입자수', y='연봉(만원)',
                        scatter_kws={'alpha':0.3, 'color':'cornflowerblue'}, # 산점도 점 설정 (반투명 파랑)
                        line_kws={'color':'red', 'lw':2}, # 회귀선 설정 (빨강, 두께 2)
                        truncate=False) # 회귀선 범위를 데이터 끝까지 확장

            # 그래프 제목 및 축 라벨 설정
            plt.title('기업 규모(가입자수)와 추정 연봉의 상관관계', fontsize=16, fontweight='bold', pad=20)
            plt.xlabel('가입자수 (명)', fontsize=12)
            plt.ylabel('추정 평균 연봉 (만원)', fontsize=12)

            # 축 단위 포맷팅 (천 단위 콤마 추가)
            current_values = plt.gca().get_xticks()
            plt.gca().set_xticklabels(['{:,.0f}'.format(x) for x in current_values])

            current_values_y = plt.gca().get_yticks()
            plt.gca().set_yticklabels(['{:,.0f}'.format(x) for x in current_values_y])

            # 그리드 추가
            plt.grid(True, linestyle='--', alpha=0.5)

            plt.tight_layout()
            print("🎉 분석 완료! 회귀분석 보고서와 그래프가 생성되었습니다.")
            plt.show()

    except KeyError as e:
        print(f"오류: 데이터에 필요한 변수명이 없습니다. 컬럼명을 확인해 주세요.\n누락된 열: {e}")
    except Exception as e:
        print(f"분석 중 예기치 않은 오류가 발생했습니다: {e}")