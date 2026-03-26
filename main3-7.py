import pandas as pd
import os

# 1. 파일 경로 및 저장 경로 설정 (cp949 인코딩)
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3\3_PAproject_3_3_NPS.csv"
save_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3"
output_file = os.path.join(save_path, "SK계열사_연봉비교_결과.xlsx")

print("데이터를 불러오고 분석을 시작합니다...")

try:
    # 데이터 불러오기
    df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

    # 2. 사업장가입상태코드가 1(정상)인 기업 필터링
    df_active = df[df['사업장가입상태코드'] == 1].copy()

    # 4. "사업장명"에 "에스케이"가 포함된 기업 필터링
    # .str.contains()를 사용하면 특정 단어가 포함된 모든 데이터를 쉽게 찾을 수 있습니다.
    df_sk = df_active[df_active['사업장명'].str.contains('에스케이', na=False)].copy()

    if df_sk.empty:
        print("조건에 맞는 '에스케이' 계열사 데이터가 존재하지 않습니다.")
    else:
        # 3. 인당금액 및 연봉 계산
        df_sk['인당금액'] = df_sk['당월고지금액'] / df_sk['가입자수']
        df_sk['연봉(원)'] = (df_sk['인당금액'] / 0.095) * 12

        # 가독성을 위해 만원 단위로 변환
        df_sk['연봉(만원)'] = df_sk['연봉(원)'] / 10000

        # 여러 지사가 있는 경우를 대비해 기업명 기준으로 병합 (가입자수는 더하고, 연봉은 평균)
        df_grouped = df_sk.groupby('사업장명').agg({
            '가입자수': 'sum',
            '연봉(만원)': 'mean'
        }).reset_index()

        # 연봉이 높은 순서대로 내림차순 정렬
        df_grouped = df_grouped.sort_values(by='연봉(만원)', ascending=False)

        # 엑셀에 깔끔하게 저장되도록 소수점 버림(정수형 변환)
        df_grouped['연봉(만원)'] = df_grouped['연봉(만원)'].astype(int)

        # 5. 결과를 엑셀 파일로 저장
        df_grouped.to_excel(output_file, index=False)

        print("\n=== SK 계열사 연봉 분석 요약 ===")
        print(f"검색된 SK 계열사 수: 총 {len(df_grouped)}개")

        # 하이닉스 순위 살짝 확인해보기 (데이터에 존재할 경우)
        hynix_data = df_grouped[df_grouped['사업장명'] == '에스케이하이닉스 주식회사']
        if not hynix_data.empty:
            rank = df_grouped[df_grouped['사업장명'] == '에스케이하이닉스 주식회사'].index[0] + 1
            print(f"* 에스케이하이닉스 주식회사는 전체 {len(df_grouped)}개 중 대략 {rank}위 수준입니다.")

        print(f"\n🎉 분석 완료! 전체 계열사 리스트가 아래 경로에 엑셀로 저장되었습니다:\n{output_file}")

except KeyError as e:
    print(f"데이터에 해당 변수명이 존재하지 않습니다. 오탈자를 확인해 주세요: {e}")
except Exception as e:
    print(f"분석 중 오류가 발생했습니다: {e}")
