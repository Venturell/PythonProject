import pandas as pd
import scipy.stats as stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd

# 1 & 7. 파일 경로 설정 및 데이터 불러오기 (cp949 인코딩 유지)
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3\3_PAproject_3_3_NPS.csv"

print("데이터를 불러오고 분석을 시작합니다...")
# DtypeWarning 방지를 위해 low_memory=False 옵션 적용
df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

try:
    # 2. 필터링: 사업장가입상태코드 1(정상) & 가입자수 200명 이상 기업
    df_filtered = df[(df['사업장가입상태코드'] == 1) & (df['가입자수'] >= 200)].copy()

    # 사업장업종코드를 안전하게 숫자(int)로 변환
    df_filtered['사업장업종코드'] = pd.to_numeric(df_filtered['사업장업종코드'], errors='coerce')

    # 5. 타겟 업종코드 4개 필터링
    target_codes = [722000, 551001, 671202, 724000]
    df_target = df_filtered[df_filtered['사업장업종코드'].isin(target_codes)].copy()

    if df_target.empty:
        print("조건에 맞는 업종코드 데이터가 존재하지 않습니다.")
    else:
        # 3 & 4. 인당금액 및 연봉 계산
        df_target['인당금액'] = df_target['당월고지금액'] / df_target['가입자수']
        df_target['연봉'] = (df_target['인당금액'] / 0.095) * 12

        # 가독성을 위해 만원 단위 변환 칼럼 추가
        df_target['연봉(만원)'] = df_target['연봉'] / 10000

        # --- 6. 코드별 포함된 기업 수 및 평균 연봉 확인 ---
        summary = df_target.groupby('사업장업종코드').agg(
            기업수=('사업장명', 'count'),
            평균연봉_만원=('연봉(만원)', 'mean')
        ).reset_index()

        # 보기 좋게 정수형으로 변환
        summary['평균연봉_만원'] = summary['평균연봉_만원'].astype(int)

        print("\n=== [1단계] 업종코드별 기업 수 및 평균 연봉 ===")
        print(summary.to_string(index=False))
        print("===============================================\n")

        # --- 5 & 6. ANOVA (분산분석) 수행 ---
        print("통계적 유의성을 검증하기 위해 ANOVA를 수행합니다...")

        # 각 업종코드별로 연봉 데이터를 리스트로 분리하여 준비
        groups = [df_target[df_target['사업장업종코드'] == code]['연봉'] for code in target_codes if
                  not df_target[df_target['사업장업종코드'] == code].empty]

        # 비교할 그룹이 2개 이상일 때만 ANOVA 실행 가능
        if len(groups) > 1:
            f_stat, p_val = stats.f_oneway(*groups)

            print("\n=== [2단계] ANOVA 검증 결과 ===")
            print(f"F-통계량(F-statistic): {f_stat:.4f}")
            print(f"p-value: {p_val:.4e}")

            # 통계적 유의성(p-value 0.05 기준) 판단
            if p_val < 0.05:
                print("\n[결론] p-value가 0.05보다 작으므로, 업종 간 연봉 차이는 통계적으로 유의미합니다.")
                print("어떤 업종끼리 차이가 나는지 사후검증(Tukey HSD)을 진행합니다.\n")

                # --- 6. 사후검증 (Tukey HSD) 수행 ---
                print("=== [3단계] 사후검증(Tukey HSD) 결과 ===")
                # endog: 결과 변수(연봉), groups: 그룹 변수(업종코드)
                tukey_result = pairwise_tukeyhsd(endog=df_target['연봉'], groups=df_target['사업장업종코드'], alpha=0.05)
                print(tukey_result)
                print("(* 'reject=True'인 항목이 두 업종 간 연봉 차이가 확실하게 존재한다는 뜻입니다.)")

            else:
                print("\n[결론] p-value가 0.05 이상이므로, 업종 간 연봉 차이는 통계적으로 유의미하지 않습니다 (우연한 차이일 수 있음).")
        else:
            print("\n비교할 업종 그룹이 충분하지 않아 ANOVA를 수행할 수 없습니다.")

except KeyError as e:
    print(f"데이터에 해당 변수명이 존재하지 않습니다. 오탈자를 확인해 주세요: {e}")
except Exception as e:
    print(f"분석 중 오류가 발생했습니다: {e}")