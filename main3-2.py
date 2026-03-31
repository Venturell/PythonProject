import pandas as pd
import matplotlib.pyplot as plt
import platform

# --- 한글 폰트 깨짐 방지 설정 ---
# 사용 중이신 윈도우 환경에 맞춰 '맑은 고딕' 폰트를 기본으로 설정합니다.
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
# 그래프에서 마이너스(-) 기호가 깨지는 것을 방지합니다.
plt.rcParams['axes.unicode_minus'] = False

# 1 & 4. 파일 경로 설정 및 데이터 불러오기 (cp949 인코딩)
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3\3_PAproject_3_3_NPS.csv"

print("데이터를 불러오고 분석을 시작합니다...")
try:
    df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

    # 2. "법정동주소광역시도코드"가 11(서울) 또는 41(경기)인 데이터 필터링
    # isin() 함수를 사용하면 두 개 이상의 조건을 한 번에 쉽게 필터링할 수 있습니다.
    df_seoul_gyeonggi = df[df['법정동주소광역시도코드'].isin([11, 41])].copy()

    if df_seoul_gyeonggi.empty:
        print("조건에 맞는 서울/경기 지역 데이터가 없습니다.")
    else:
        # 3. 가입자수 기준으로 상위 10개 기업 추출
        top_10_companies = df_seoul_gyeonggi.nlargest(10, '가입자수')[['사업장명', '가입자수']]

        # --- 텍스트 결과 출력 추가 ---
        print("=== 서울/경기 가입자수 상위 10개 기업 리스트 ===")
        print(top_10_companies.to_string(index=False))
        # ---------------------------
        # --- 그래프 그리기 ---
        plt.figure(figsize=(12, 6))  # 그래프의 가로, 세로 크기 설정

        # 바 그래프 생성 (x축: 사업장명, y축: 가입자수)
        # color 인자를 통해 그래프 색상을 보기 편한 색으로 지정했습니다.
        plt.bar(top_10_companies['사업장명'], top_10_companies['가입자수'], color='cornflowerblue')

        # 그래프 제목 및 축 이름 설정
        plt.title('서울/경기 지역 가입자 수 Top 10 기업', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('사업장명', fontsize=12)
        plt.ylabel('가입자 수 (명)', fontsize=12)

        # 기업 이름이 길 경우 글자가 겹치지 않도록 x축 라벨을 45도 기울여 줍니다.
        plt.xticks(rotation=45, ha='right')

        # 각 바 위에 정확한 가입자 수 숫자를 표시해 주는 추가 기능
        for index, value in enumerate(top_10_companies['가입자수']):
            # 천 단위마다 콤마(,)를 찍어서 숫자를 읽기 쉽게 포맷팅합니다.
            plt.text(index, value, f'{value:,}', ha='center', va='bottom', fontsize=10)

        # 그래프 여백을 자동으로 예쁘게 조절
        plt.tight_layout()

        # 완성된 그래프를 화면에 띄움
        print("🎉 분석 완료! 그래프 창이 열립니다.")
        plt.show()

except FileNotFoundError:
    print(f"파일을 찾을 수 없습니다. 경로를 확인해 주세요:\n{file_path}")
except KeyError as e:
    print(f"데이터에 해당 변수명이 존재하지 않습니다. 오탈자를 확인해 주세요: {e}")
except Exception as e:
    print(f"분석 중 오류가 발생했습니다: {e}")