import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import platform
import warnings

warnings.filterwarnings('ignore')  # 불필요한 경고 메시지 숨김

# --- 1. 한글 폰트 및 마이너스 기호 깨짐 방지 설정 ---
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')  # 윈도우 맑은 고딕
plt.rcParams['axes.unicode_minus'] = False

# --- 2. 데이터 불러오기 ---
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#2\2_PAproject_2_3_EDA.csv"

print("데이터를 불러오고 전처리를 시작합니다...")

try:
    df = pd.read_csv(file_path, encoding='cp949', low_memory=False)

    # --- 3. 이탈 여부(퇴사) 기준 생성 ---
    # Termination_Date(퇴사일)가 비어있지 않다(notnull)면 퇴사자(1), 비어있다면 재직자(0)로 간주합니다.
    df['Is_Terminated'] = df['Termination_Date'].notnull().astype(int)

    # --- 4. 데이터 집계 (Grouping) ---

    # [데이터 1] 부서(Department) 및 직무(Job_Role)별 이탈율 계산
    # 퇴사자 수를 해당 그룹의 전체 인원으로 나누어 평균(mean)을 구한 뒤 100을 곱해 퍼센트(%)로 만듭니다.
    dept_role_turnover = df.groupby(['Department', 'Job_Role'])['Is_Terminated'].mean().reset_index()
    dept_role_turnover['Turnover_Rate(%)'] = dept_role_turnover['Is_Terminated'] * 100

    # 히트맵을 그리기 위해 데이터를 피벗 테이블 형태로 변환 (행: 부서, 열: 직무, 값: 이탈율)
    heatmap_data = dept_role_turnover.pivot(index='Department', columns='Job_Role', values='Turnover_Rate(%)')

    # [데이터 2] 성과등급(Performance_Rating)별 이탈율 계산
    perf_turnover = df.groupby('Performance_Rating')['Is_Terminated'].mean().reset_index()
    perf_turnover['Turnover_Rate(%)'] = perf_turnover['Is_Terminated'] * 100
    perf_turnover = perf_turnover.sort_values(by='Performance_Rating')  # 성과등급 순으로 정렬

    # --- 5. 시각화 진행 (Figure 1: 히트맵, Figure 2: 막대그래프) ---
    fig, axes = plt.subplots(2, 1, figsize=(14, 16))

    # [그래프 1] 부서 및 직무별 이탈율 히트맵 (Heatmap)
    # cmap="YlOrRd"는 값이 높을수록 노란색에서 진한 빨간색으로 변하게 합니다.
    sns.heatmap(heatmap_data, annot=True, fmt=".1f", cmap="YlOrRd", ax=axes[0],
                linewidths=.5, cbar_kws={'label': '이탈율 (%)'}, annot_kws={"size": 11})
    axes[0].set_title('🔥 부서(Department) 및 직무(Job_Role)별 이탈율 히트맵', fontsize=18, fontweight='bold', pad=20)
    axes[0].set_xlabel('직무 (Job Role)', fontsize=14)
    axes[0].set_ylabel('부서 (Department)', fontsize=14)
    axes[0].tick_params(axis='x', rotation=45)  # 직무 이름이 길 경우를 대비해 45도 회전

    # [그래프 2] 성과등급별 이탈율 막대그래프 (Bar Chart)
    sns.barplot(x='Performance_Rating', y='Turnover_Rate(%)', data=perf_turnover,
                palette='viridis', ax=axes[1], edgecolor='black')
    axes[1].set_title('📊 성과등급(Performance Rating)별 이탈율', fontsize=18, fontweight='bold', pad=20)
    axes[1].set_xlabel('성과등급', fontsize=14)
    axes[1].set_ylabel('이탈율 (%)', fontsize=14)

    # 막대그래프 위에 정확한 수치(%) 표시
    for p in axes[1].patches:
        axes[1].annotate(f"{p.get_height():.1f}%",
                         (p.get_x() + p.get_width() / 2., p.get_height()),
                         ha='center', va='center',
                         fontsize=13, color='black', fontweight='bold', xytext=(0, 10),
                         textcoords='offset points')

    # 레이아웃 간격 조정 및 출력
    plt.tight_layout(pad=3.0)
    print("🎉 이탈율 시각화가 완료되었습니다. 출력된 두 개의 그래프를 확인해 주세요!")
    plt.show()

except FileNotFoundError:
    print(f"오류: 지정된 경로에서 파일을 찾을 수 없습니다.\n경로: {file_path}")
except Exception as e:
    print(f"데이터 처리 중 오류가 발생했습니다: {e}")