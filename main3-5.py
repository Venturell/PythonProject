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
df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

try:
    # 2. 사업장가입상태코드 1(정상)이고, 사업장업종코드가 300100인 기업 필터링
    # (문자형과 숫자형 혼재를 막기 위해 int로 형변환 후 비교)
    df['사업장업종코드'] = pd.to_numeric(df['사업장업종코드'], errors='coerce')
    df_filtered = df[(df['사업장가입상태코드'] == 1) & (df['사업장업종코드'] == 300100)].copy()

    if df_filtered.empty:
        print("조건에 맞는 동종업계(업종코드 300100) 데이터가 없습니다.")
    else:
        # 3. 인당금액 및 연봉 계산
        df_filtered['인당금액'] = df_filtered['당월고지금액'] / df_filtered['가입자수']
        df_filtered['연봉(원)'] = (df_filtered['인당금액'] / 0.095) * 12

        # 가독성을 위해 만원 단위로 변환
        df_filtered['연봉(만원)'] = df_filtered['연봉(원)'] / 10000

        # --- 4. 동종업계 평균 vs 자사 연봉 추출 ---
        # 동종업계 전체 평균 연봉 계산
        industry_avg = df_filtered['연봉(만원)'].mean()

        # 에스케이하이닉스 주식회사 연봉 추출
        target_company_name = "에스케이하이닉스 주식회사"
        my_company_data = df_filtered[df_filtered['사업장명'] == target_company_name]

        if my_company_data.empty:
            print(f"'{target_company_name}' 데이터를 찾을 수 없습니다. 이름이 정확한지 확인해 주세요.")
        else:
            my_company_salary = my_company_data['연봉(만원)'].values[0]

            # 텍스트 결과 출력
            print("\n=== 연봉 벤치마킹 결과 ===")
            print(f"동종업계(300100) 평균: {int(industry_avg):,} 만원")
            print(f"{target_company_name}: {int(my_company_salary):,} 만원")
            print("===========================\n")

            # --- 그래프 (막대그래프) 그리기 ---
            plt.figure(figsize=(8, 6))

            # 비교할 대상과 값 리스트 설정
            labels = ['동종업계 평균', target_company_name]
            values = [industry_avg, my_company_salary]
            colors = ['lightgray', 'cornflowerblue']  # 자사를 돋보이게 색상 차별화

            # 막대그래프 생성
            bars = plt.bar(labels, values, color=colors, width=0.5, edgecolor='black')

            plt.title('동종업계 평균 vs 자사 임금 비교', fontsize=16, fontweight='bold', pad=20)
            plt.ylabel('추정 평균 연봉 (만원)', fontsize=12)

            # 5. 각 막대 위에 연봉 값(만원) 표시
            for bar in bars:
                yval = bar.get_height()
                plt.text(bar.get_x() + bar.get_width() / 2, yval + (yval * 0.01),
                         f'{int(yval):,}만원', ha='center', va='bottom', fontsize=12, fontweight='bold')

            # y축의 범위를 약간 넉넉하게 주어 텍스트가 잘리지 않게 조정
            plt.ylim(0, max(values) * 1.15)

            plt.tight_layout()
            print("🎉 보상 벤치마킹 분석 완료! 그래프 창이 열립니다.")
            plt.show()

except KeyError as e:
    print(f"데이터에 해당 변수명이 존재하지 않습니다. 오탈자를 확인해 주세요: {e}")
except Exception as e:
    print(f"분석 중 오류가 발생했습니다: {e}")