import pandas as pd
import statsmodels.api as sm
import os

# 1 & 6. 파일 경로 설정 및 데이터 불러오기 (cp949 인코딩 유지)
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3\3_PAproject_3_3_NPS.csv"

if not os.path.exists(file_path):
    print(f"오류: 지정된 경로에 파일을 찾을 수 없습니다.\n경로: {file_path}")
else:
    print("NPS 데이터를 불러오고 분석을 준비합니다...")
    try:
        # 데이터 불러오기 (low_memory=False 적용)
        df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

        # 2. 필터링: 정상 가입(1) & 가입자수 200명 이상
        df_filtered = df[(df['사업장가입상태코드'] == 1) & (df['가입자수'] >= 200)].copy()

        # 3. 연봉 추정 계산 (원 단위)
        df_filtered['당월고지금액'] = pd.to_numeric(df_filtered['당월고지금액'], errors='coerce')
        df_filtered['가입자수'] = pd.to_numeric(df_filtered['가입자수'], errors='coerce')

        df_filtered['인당금액'] = df_filtered['당월고지금액'] / df_filtered['가입자수']
        df_filtered['연봉'] = (df_filtered['인당금액'] / 0.095) * 12

        # 4. 적용일자에서 연도 추출
        df_filtered['적용일자'] = pd.to_datetime(df_filtered['적용일자'], format='%Y-%m-%d', errors='coerce')
        df_filtered['연도'] = df_filtered['적용일자'].dt.year

        # 5. 분석 대상 산업 및 지역 필터링
        target_industry = [722000, 551001, 671202, 724000]
        target_region = [41, 11, 28, 52]

        # 코드를 숫자로 안전하게 변환
        df_filtered['사업장업종코드'] = pd.to_numeric(df_filtered['사업장업종코드'], errors='coerce')
        df_filtered['법정동주소광역시도코드'] = pd.to_numeric(df_filtered['법정동주소광역시도코드'], errors='coerce')

        # 두 가지 조건(타겟 산업 AND 타겟 지역)을 모두 만족하는 데이터만 추출
        df_final = df_filtered[(df_filtered['사업장업종코드'].isin(target_industry)) &
                               (df_filtered['법정동주소광역시도코드'].isin(target_region))].copy()

        # 분석에 사용할 변수만 남기고 결측치(빈칸) 행 제거
        vars_to_keep = ['연봉', '가입자수', '연도', '사업장업종코드', '법정동주소광역시도코드']
        df_final = df_final[vars_to_keep].dropna()

        if df_final.empty:
            print("조건에 맞는 분석 데이터가 존재하지 않습니다.")
        else:
            print(f"총 {len(df_final):,}개 기업을 대상으로 다중회귀분석을 시작합니다...\n")

            # --- 더미 코딩 (Dummy Coding) 처리 ---
            # 더미 변수로 만들기 위해 먼저 문자열(str)로 형변환합니다.
            df_final['사업장업종코드'] = df_final['사업장업종코드'].astype(int).astype(str)
            df_final['법정동주소광역시도코드'] = df_final['법정동주소광역시도코드'].astype(int).astype(str)

            # pd.get_dummies()를 사용하여 범주형 변수를 0과 1로 변환
            # drop_first=True 옵션은 다중공선성(Dummy Variable Trap)을 막기 위해 기준점(Reference) 그룹을 하나 빼는 필수 설정입니다.
            df_dummy = pd.get_dummies(df_final, columns=['사업장업종코드', '법정동주소광역시도코드'], drop_first=True, dtype=int)

            # --- 회귀분석 (OLS) 수행 ---
            # 종속변수 (y)
            y = df_dummy['연봉']
            # 독립변수 (X) - 연봉을 제외한 나머지 모든 변수
            X = df_dummy.drop('연봉', axis=1)
            # 상수항 추가
            X = sm.add_constant(X)

            # 모델 생성 및 피팅
            model = sm.OLS(y, X)
            results = model.fit()

            # 결과 보고서 출력
            print("=" * 80)
            print("### [다중회귀분석 결과: 산업/지역/규모/업력 종합] ###")
            print("=" * 80)
            print(results.summary())
            print("=" * 80)
            print("\n🎉 모든 변수를 종합한 회귀분석이 성공적으로 완료되었습니다!")

    except Exception as e:
        print(f"분석 중 예기치 않은 오류가 발생했습니다: {e}")
