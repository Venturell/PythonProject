import pandas as pd
import requests
import datetime
import os
import warnings

warnings.filterwarnings('ignore')

#직원들의집을구글맵/네이버맵으로지오코딩-자차운전
# ==========================================
# --- 1. API 키 및 기본 설정 ---
# ==========================================
# 🚨 본인의 네이버 클라우드 플랫폼 API 키를 입력하세요.
NAVER_CLIENT_ID = "네이버id이벽"
NAVER_CLIENT_SECRET = "네이버시크릿키입력"

# 헤더 설정
HEADERS = {
    "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
    "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
}

# 회사 위치 및 시간 설정
COMPANY_ADDRESS = "서울특별시 종로구 청계천로 1"

# 특정 날짜(예: 다가오는 월요일 또는 평일)의 07:30, 18:30 설정
# API에서 미래 교통상황 예측을 위해 YYYY-MM-DDTHH:mm:ss 형식을 사용합니다.
today = datetime.datetime.now()
# 만약 주말이라면 평일(월요일)로 기준일 조정 (정확한 평일 트래픽 반영을 위함)
days_ahead = 0 if today.weekday() < 5 else (7 - today.weekday())
target_date = today + datetime.timedelta(days=days_ahead)

time_to_work = target_date.replace(hour=7, minute=30, second=0).strftime('%Y-%m-%dT%H:%M:%S')
time_to_home = target_date.replace(hour=18, minute=30, second=0).strftime('%Y-%m-%dT%H:%M:%S')

# 파일 경로
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#10\10_PAproject_10_3_Address.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "10_PAproject_10_3_CommuteTime.xlsx")


# ==========================================
# --- 2. API 통신용 핵심 함수 ---
# ==========================================
def get_geocode(address):
    """주소를 위도(lat), 경도(lon)로 변환"""
    if pd.isna(address):
        return None
    url = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
    params = {"query": str(address)}
    try:
        res = requests.get(url, headers=HEADERS, params=params)
        if res.status_code == 200:
            data = res.json()
            if data.get('addresses'):
                return f"{data['addresses'][0]['x']},{data['addresses'][0]['y']}"  # "경도,위도" 포맷 반환
    except Exception as e:
        print(f"좌표 변환 오류 ({address}): {e}")
    return None


def get_driving_time(start_coord, goal_coord, departure_time):
    """Direction API를 통해 출발지->목적지 운전 소요시간(분) 계산"""
    if not start_coord or not goal_coord:
        return None

    url = "https://maps.apigw.ntruss.com/map-direction/v1/driving"
    params = {
        "start": start_coord,
        "goal": goal_coord,
        "option": "trafast",  # 실시간/예측 빠른길 기준
        "departureTime": departure_time  # 출발 시간
    }

    try:
        res = requests.get(url, headers=HEADERS, params=params)
        if res.status_code == 200:
            data = res.json()
            # trafast 경로가 존재하는 경우
            if 'route' in data and 'trafast' in data['route']:
                # duration은 밀리초(ms) 단위로 반환되므로 분 단위로 변환 (ms -> 초 -> 분)
                duration_ms = data['route']['trafast'][0]['summary']['duration']
                return round(duration_ms / 1000 / 60)
    except Exception as e:
        print(f"길찾기 오류: {e}")
    return None


# ==========================================
# --- 3. 데이터 로드 및 분석 수행 ---
# ==========================================
print("데이터를 불러오고 회사 좌표를 확인합니다...")
df = pd.read_excel(file_path)

# 1) 회사 위치 좌표 변환
company_coord = get_geocode(COMPANY_ADDRESS)
if not company_coord:
    print("❌ 회사의 위치 좌표를 찾을 수 없습니다. 주소나 API 상태를 확인해 주세요.")
    exit()

print(f"🏢 회사 좌표 확보 완료 ({COMPANY_ADDRESS})\n")

# 2) gtw가 'driving'인 직원만 필터링 (대소문자 무시 및 공백 제거)
df_driving = df[df['gtw'].astype(str).str.strip().str.lower() == 'driving'].copy()
print(f"🚗 총 {len(df_driving)}명의 자차 출퇴근(driving) 직원에 대해 계산을 시작합니다.")

to_work_times = []
to_home_times = []
total_times = []

# 3) 직원별 통근 시간 계산
for idx, row in df_driving.iterrows():
    home_address = row['address']
    home_coord = get_geocode(home_address)

    if home_coord:
        # 출근: 집(start) -> 회사(goal) / 07:30
        t_work = get_driving_time(home_coord, company_coord, time_to_work)
        # 퇴근: 회사(start) -> 집(goal) / 18:30
        t_home = get_driving_time(company_coord, home_coord, time_to_home)

        # 합계 계산
        if t_work is not None and t_home is not None:
            t_total = t_work + t_home
        else:
            t_total = None

        to_work_times.append(t_work)
        to_home_times.append(t_home)
        total_times.append(t_total)
    else:
        to_work_times.append(None)
        to_home_times.append(None)
        total_times.append(None)

    if (len(to_work_times)) % 10 == 0:
        print(f"  -> {len(to_work_times)} / {len(df_driving)}명 처리 완료...")

# ==========================================
# --- 4. 결과 저장 ---
# ==========================================
# 데이터프레임에 결과 파생 변수 추가
df_driving['출근_운전시간(분)'] = to_work_times
df_driving['퇴근_운전시간(분)'] = to_home_times
df_driving['총_운전시간(분)'] = total_times

# 전체 원본 데이터와 병합하기 위해, 원래 df에 결과를 업데이트(Left Join 방식)
# (driving이 아닌 사람들은 해당 컬럼이 비어있게 됨)
df_final = df.merge(
    df_driving[['출근_운전시간(분)', '퇴근_운전시간(분)', '총_운전시간(분)']],
    left_index=True,
    right_index=True,
    how='left'
)

# 엑셀로 저장
df_final.to_excel(output_path, index=False)

print("\n" + "=" * 60)
print(f"✅ 통근 시간(운전) 계산이 완료되었습니다.")
print(f"💾 저장 경로: {output_path}")
print("=" * 60)