import pandas as pd
from google import genai
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# --- 1. API 키 및 모델 설정 ---
# ==========================================
# 🚨 여기에 Google AI Studio에서 발급받은 API 키를 입력하세요!
API_KEY = "AI어쩌구API키입력하는곳"
client = genai.Client(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash'

# ==========================================
# --- 2. 파일 경로 설정 ---
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#5\5_Paproject_5_6_360.xlsx"
output_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#5\5_PAproject_5_6_360_Summary.xlsx"

print("데이터를 불러오고 있습니다...")
df = pd.read_excel(file_path)


# ==========================================
# --- 3. AI 텍스트 요약 함수 정의 ---
# ==========================================
def generate_summary(text_data, target_name, group_type):
    """주어진 텍스트 데이터를 Gemini API를 통해 요약하는 함수"""
    # 프롬프트 엔지니어링: AI에게 역할과 요약 형식을 명확히 지정
    prompt = f"""
    당신은 기업의 인사평가(HR) 전문가입니다. 
    다음은 {group_type} '{target_name}'에 대한 상사, 동료, 부하직원들의 360도 다면평가 피드백 모음입니다.

    이 피드백들을 종합하여 다음 세 가지 항목으로 깔끔하게 요약해 주세요:
    1. 핵심 강점 (1~2문장)
    2. 보완할 점 (1~2문장)
    3. 종합 평가 및 제언 (1~2문장)

    [피드백 텍스트 모음]
    {text_data}
    """

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"요약 실패 (오류: {e})"


def process_and_summarize(df, group_col, group_name_kor):
    """데이터프레임을 그룹화하고 각 그룹별로 요약을 수행하는 함수"""
    summary_results = []
    grouped = df.groupby(group_col)

    print(f"\n▶ [{group_name_kor}별 요약 시작] (총 {len(grouped)}개 그룹)")

    for name, group in grouped:
        print(f" - '{name}' 요약 진행 중...")
        # 해당 그룹의 모든 피드백 텍스트를 하나의 거대한 문자열로 결합 (결측치는 무시)
        combined_text = "\n".join(group['feedback_text'].dropna().astype(str).tolist())

        # 텍스트가 너무 짧거나 없을 경우 방어 코드
        if len(combined_text.strip()) < 10:
            summary = "피드백 데이터가 충분하지 않습니다."
        else:
            summary = generate_summary(combined_text, name, group_name_kor)

        summary_results.append({
            group_col: name,
            'AI_종합_요약': summary
        })

    return pd.DataFrame(summary_results)


# ==========================================
# --- 4. 그룹별 요약 실행 ---
# ==========================================
# API 호출 시간이 소요되므로 진행 상황이 출력됩니다.
df_employee = process_and_summarize(df, 'employee_name', '개별 직원')
df_department = process_and_summarize(df, 'department', '부서')
df_job_level = process_and_summarize(df, 'job_level', '직급')

# ==========================================
# --- 5. 결과를 엑셀로 저장 ---
# ==========================================
print(f"\n모든 요약이 완료되었습니다. 엑셀 파일로 저장 중입니다...")

try:
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_employee.to_excel(writer, sheet_name='1. Employee_Summary', index=False)
        df_department.to_excel(writer, sheet_name='2. Department_Summary', index=False)
        df_job_level.to_excel(writer, sheet_name='3. Job_Level_Summary', index=False)

    print(f"✅ 엑셀 파일 저장 성공! \n저장 경로: {output_path}")

except Exception as e:
    print(f"❌ 엑셀 저장 중 오류가 발생했습니다: {e}")