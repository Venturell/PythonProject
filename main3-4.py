import pandas as pd
import matplotlib.pyplot as plt
import platform

# --- 5. 한글 폰트 및 마이너스 기호 깨짐 방지 설정 ---
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# 1. 파일 경로 설정 및 데이터 불러오기
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#3\3_PAproject_3_3_NPS.csv"

print("데이터를 불러오고 분석을 시작합니다...")
# 변수명이 한글이므로 cp949 인코딩 유지, DtypeWarning 방지를 위해 low_memory=False 사용
df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

try:
    # 2. 사업장가입상태코드가 1(정상)이고, 사업장업종코드가 300100인 기업 필터링
    # 업종코드가 숫자형(int/float)이거나 문자형(str)일 수 있으므로 안전하게 처리합니다.
    # 만약 에러가 난다면 df['사업장업종코드'] == '300100' 처럼 따옴표를 씌워보세요.
    df_filtered = df[(df['사업장가입상태코드'] == 1) & (df['사업장업종코드'] == 300100)].copy()

    if df_filtered.empty:
        print("조건에 맞는 기업(상태 1, 업종 300100) 데이터가 존재하지 않습니다.")
    else:
        # 3. "순유입" 변수 생성 (신규취득자수 - 상실가입자수)
        df_filtered['순유입'] = df_filtered['신규취득자수'] - df_filtered['상실가입자수']

        # 4. 순유입 기준 상위 10개 기업 추출
        top_10_inflow = df_filtered.nlargest(10, '순유입')[['사업장명', '순유입']]

        # 결과를 텍스트로도 깔끔하게 출력
        print("\n=== 동종업계(300100) 순유입 상위 10개 기업 ===")
        print(top_10_inflow.to_string(index=False))
        print("=" * 45)

        # --- 그래프 (막대그래프) 그리기 ---
        plt.figure(figsize=(12, 6))

        # 기업명(x축)과 순유입 수(y축)로 막대그래프 생성
        bars = plt.bar(top_10_inflow['사업장명'], top_10_inflow['순유입'], color='mediumseagreen', edgecolor='black')

        plt.title('동종업계(업종코드:300100) 순유입 Top 10 기업', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('사업장명', fontsize=12)
        plt.ylabel('순유입 인원 (명)', fontsize=12)

        # 기업명이 겹치지 않게 45도 기울이기
        plt.xticks(rotation=45, ha='right')

        # 각 막대 위에 순유입 인원 숫자를 표시
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2, yval + (yval * 0.02),
                     f'{int(yval):,}명', ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        print("🎉 순유입 분석 완료! 그래프 창이 열립니다.")
        plt.show()

except KeyError as e:
    print(f"데이터에 해당 변수명이 존재하지 않습니다. 오탈자를 확인해 주세요: {e}")
except Exception as e:
    print(f"분석 중 오류가 발생했습니다: {e}")