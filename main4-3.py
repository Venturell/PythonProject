import pandas as pd
import statsmodels.api as sm
import os

# --- 회귀분석 상세 보고서 출력 코드 ---

# 1. 파일 경로 및 저장 경로 설정 (cp949 인코딩 유지)
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3\3_PAproject_3_3_NPS.csv"

if not os.path.exists(file_path):
    print(f"오류: 지정된 경로에 파일을 찾을 수 없습니다.\n경로: {file_path}")
else:
    print("NPS 데이터를 불러오고 분석을 시작합니다...")
    try:
        # 2. 데이터 불러오기 (low_memory=False 옵션 적용)
        df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

        # 3. 필터링: 사업장가입상태코드 1(정상) & 가입자수 200명 이상 기업
        df_filtered = df[(df['사업장가입상태코드'] == 1) & (df['가입자수'] >= 200)].copy()

        if df_filtered.empty:
            print("조건에 맞는 200인 이상 정상 가입 기업 데이터가 존재하지 않습니다.")
        else:
            # 4. 연봉 계산 (이미지 스케일에 맞추기 위해 '원' 단위 그대로 사용)
            df_filtered['인당금액'] = df_filtered['당월고지금액'] / df_filtered['가입자수']
            df_filtered['연봉'] = (df_filtered['인당금액'] / 0.095) * 12

            # 5. 적용일자에서 연도 추출
            df_filtered['적용일자'] = pd.to_datetime(df_filtered['적용일자'], format='%Y-%m-%d', errors='coerce')
            df_filtered['연도'] = df_filtered['적용일자'].dt.year

            # 6. 회귀분석을 위해 결측치 제거
            df_reg = df_filtered.dropna(subset=['연도', '연봉']).copy()

            # --- OLS 회귀분석 수행 (statsmodels 사용) ---
            print("가입연도와 연봉 간의 상세 회귀분석 보고서를 생성합니다...\n\n")

            # 종속변수 (y): 연봉 (원 단위)
            y = df_reg['연봉']
            # 독립변수 (X): 연도
            X = df_reg['연도']
            # statsmodels는 절편(const)을 직접 추가해 주어야 합니다.
            X = sm.add_constant(X)

            # OLS 모델 생성 및 피팅
            model = sm.OLS(y, X)
            results = model.fit()

            # --- 결과 출력 ---
            # 올려주신 이미지 2와 동일한 포맷의 상세 보고서 출력
            print("### [회귀 분석 결과 보고서] ###")
            print("-" * 75)
            # results.summary()가 핵심 명령어입니다.
            print(results.summary())
            print("-" * 75)
            print("\n🎉 회귀분석 결과 보고서 생성이 완료되었습니다.")

    except KeyError as e:
        print(f"오류: 데이터프레임에 필요한 열이 없습니다. 컬럼명을 확인해 주세요.\n누락된 열: {e}")
    except Exception as e:
        print(f"분석 중 예기치 않은 오류가 발생했습니다: {e}")