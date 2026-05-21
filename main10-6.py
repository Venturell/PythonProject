import pandas as pd
import googlemaps
from datetime import datetime, timedelta
import os
import warnings

warnings.filterwarnings('ignore')

#직원들의집을구글맵/네이버맵으로지오코딩-대중교통
# ==========================================
# --- 1. API 키 및 기본 설정 ---
# ==========================================
# 🚨 본인의 Google Maps API 키를 입력하세요.
GOOGLE_API_KEY = "googleapikey입력"
gmaps = googlemaps.Client(key=GOOGLE_API_KEY)

# 회사 위치 설정
COMPANY_ADDRESS = "서울특별시 종로구 청계천로 1"

# 출발 시간 설정 (오늘 기준 가장 가까운 평일의 07:30, 18:30)
# 대중교통 배차 간격 등은 요일/시간의 영향을 크게 받으므로 정확한 datetime 객체가 필요합니다.
now = datetime.now()
days_ahead = 0 if now.weekday() < 5 else (7 - now.weekday())  # 주말이면 다음 주 월요일로
target_date = now + timedelta(days=days_ahead)

time_to_work = target_date.replace(hour=7, minute=30, second=0, microsecond=0)
time_to_home = target_date.replace(hour=18, minute=30, second=0, microsecond=0)

# 파일 경로 설정
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#10\10_PAproject_10_3_Address.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "10_PAproject_10_3_TransitTime.xlsx")


# ==========================================
# --- 2. API 통신용 핵심 함수 ---
# ==========================================
def get_transit_time(origin, destination, departure_time):
    """
    Google Distance Matrix API를 사용하여 대중교통 소요시간(분) 계산
    (주소 텍스트를 그대로 넣어도 구글이 알아서 좌표로 변환하여 계산해 줍니다.)
    """
    if pd.isna(origin) or pd.isna(destination):
        return None

    try:
        # distance_matrix 요청
        result = gmaps.distance_matrix(
            origins=str(origin),
            destinations=str(destination),
            mode="transit",  # 대중교통 모드
            departure_time=departure_time,  # 출발 시간
            language="ko"
        )

        # 응답 데이터 파싱
        if result['status'] == 'OK':
            element = result['rows'][0]['elements'][0]
            if element['status'] == 'OK':
                # duration은 '초(seconds)' 단위로 반환되므로 '분(minutes)'으로 변환
                duration_sec = element['duration']['value']
                return round(duration_sec / 60)
            else:
                # 경로를 찾을 수 없는 경우 (예: 너무 멀거나 대중교통이 없는 경우)
                print(f"경로 없음: {origin} -> {destination}")
                return None
    except Exception as e:
        print(f"API 오류 발생 ({origin}): {e}")

    return None


# ==========================================
# --- 3. 데이터 로드 및 분석 수행 ---
# ==========================================
print("데이터를 불러오고 분석을 준비합니다...\n")
df = pd.read_excel(file_path)

# gtw 변수가 'transit'인 사람만 필터링 (대소문자 및 공백 무시)
df_transit = df[df['gtw'].astype(str).str.strip().str.lower() == 'transit'].copy()
print(f"🚌 총 {len(df_transit)}명의 대중교통(transit) 이용 직원에 대해 계산을 시작합니다.")
print("   (Google API 호출 중... 시간이 다소 소요될 수 있습니다.)")

to_work_times = []
to_home_times = []
total_times = []

# 직원별 통근 시간 계산 루프
for idx, row in df_transit.iterrows():
    home_address = row['address']

    # 1. 출근: 집(origin) -> 회사(destination) / 07:30 출발
    t_work = get_transit_time(
        origin=home_address,
        destination=COMPANY_ADDRESS,
        departure_time=time_to_work
    )

    # 2. 퇴근: 회사(origin) -> 집(destination) / 18:30 출발
    t_home = get_transit_time(
        origin=COMPANY_ADDRESS,
        destination=home_address,
        departure_time=time_to_home
    )

    # 3. 총 시간 합계 계산
    if t_work is not None and t_home is not None:
        t_total = t_work + t_home
    else:
        t_total = None

    to_work_times.append(t_work)
    to_home_times.append(t_home)
    total_times.append(t_total)

    # 진행률 표시 (10건마다)
    current_count = len(to_work_times)
    if current_count % 10 == 0 or current_count == len(df_transit):
        print(f"  -> {current_count} / {len(df_transit)}명 처리 완료...")

# ==========================================
# --- 4. 결과 통합 및 저장 ---
# ==========================================
# 분석된 시간 데이터를 임시 데이터프레임에 할당
df_transit['출근_대중교통(분)'] = to_work_times
df_transit['퇴근_대중교통(분)'] = to_home_times
df_transit['총_대중교통(분)'] = total_times

# 전체 원본 데이터(df)와 병합 (Left Join)
# transit이 아닌 직원의 해당 컬럼은 빈칸(NaN)으로 남게 됩니다.
df_final = df.merge(
    df_transit[['출근_대중교통(분)', '퇴근_대중교통(분)', '총_대중교통(분)']],
    left_index=True,
    right_index=True,
    how='left'
)

# 엑셀 파일로 저장
df_final.to_excel(output_path, index=False)

print("\n" + "=" * 60)
print(f"✅ 대중교통 통근 시간 계산이 모두 완료되었습니다.")
print(f"💾 저장 경로: {output_path}")
print("=" * 60)