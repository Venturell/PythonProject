import pandas as pd

# 1. 파일 경로 설정 (경로명 앞 r 붙임)
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3\3_PAproject_3_3_NPS.csv"

try:
    # 6. 한글 변수명이 포함된 데이터이므로 cp949 인코딩으로 불러오기
    print("NPS 데이터를 불러오는 중입니다...")
    df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

    # 2. 조건 필터링: 사업장가입상태코드가 1(정상)이고, 가입자수가 2000명 이상인 기업
    # (결측치나 오류 데이터 방지를 위해 필터링을 먼저 진행합니다)
    df_filtered = df[(df['사업장가입상태코드'] == 1) & (df['가입자수'] >= 2000)].copy()

    if df_filtered.empty:
        print("조건에 맞는 기업(가입자 2000명 이상, 상태코드 1)이 없습니다.")
    else:
        # 3. "인당금액" 계산 = 당월고지금액 / 가입자수
        df_filtered['인당금액'] = df_filtered['당월고지금액'] / df_filtered['가입자수']

        # 4. "연봉" 계산 = (인당금액 / 0.095) * 12
        # (국민연금 요율 9.5%를 나누어 월급여를 구한 뒤 12개월을 곱해 연봉 추산)
        df_filtered['연봉(원)'] = (df_filtered['인당금액'] / 0.095) * 12

        # 6. 연봉을 '만원' 단위로 변환 및 보기 좋게 정수형으로 처리
        df_filtered['연봉(만원)'] = (df_filtered['연봉(원)'] / 10000).astype(int)

        # 5. 연봉이 높은 순서로 상위 10개 기업 선정 (사업장명, 가입자수, 연봉 추출)
        top_10_companies = df_filtered.nlargest(10, '연봉(만원)')[['사업장명', '가입자수', '연봉(만원)']]

        # 인덱스(행 번호)를 1부터 10까지 깔끔하게 재설정
        top_10_companies.reset_index(drop=True, inplace=True)
        top_10_companies.index = top_10_companies.index + 1

        # 결과 표 출력
        print("\n🏆 [가입자 2000명 이상 대기업 평균 연봉 Top 10] 🏆")
        print("-" * 50)
        print(top_10_companies)
        print("-" * 50)

except FileNotFoundError:
    print(f"파일을 찾을 수 없습니다. 경로를 확인해 주세요:\n{file_path}")
except KeyError as e:
    print(f"데이터에 해당 변수명이 존재하지 않습니다. 띄어쓰기나 오탈자를 확인해 주세요: {e}")
except Exception as e:
    print(f"분석 중 오류가 발생했습니다: {e}")