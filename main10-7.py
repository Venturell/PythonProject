import pandas as pd
import requests
import googlemaps
import datetime
import os
import warnings

warnings.filterwarnings('ignore')

#직원들의집을구글맵/네이버맵으로지오코딩-통합
# ==========================================
# --- 1. API 키 및 기본 설정 ---
# ==========================================
# 🚨 1) 네이버 API 키 (자차 운전용)
NAVER_CLIENT_ID = "네이버apiID"
NAVER_CLIENT_SECRET = "네이버SECRET"

NAVER_HEADERS = {
    "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
    "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
}

# 🚨 2) 구글 API 키 (대중교통용)
GOOGLE_API_KEY = "구글API키입력"
gmaps = googlemaps.Client(key=GOOGLE_API_KEY)

# 회사 위치 설정
COMPANY_ADDRESS = "서울특별시 종로구 청계천로 1"

# 파일 경로
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#10\10_PAproject_10_3_Address.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "10_PAproject_10_3_CommuteTime_Total.xlsx")

# ==========================================
# --- 2. 출퇴근 시간 기준 설정 (가장 가까운 평일) ---
# ==========================================
# 주말 교통상황 왜곡을 방지하기 위해 다가오는 평일 기준으로 세팅합니다.
now = datetime.datetime.now()
days_ahead = 0 if now.weekday() < 5 else (7 - now.weekday())
target_date = now + datetime.timedelta(days=days_ahead)

# 구글 API용 (datetime 객체)
dt_to_work = target_date.replace(hour=7, minute=30, second=0, microsecond=0)
dt_to_home = target_date.replace(hour=18, minute=30, second=0, microsecond=0)

# 네이버 API용 (문자열 형식)
str_to_work = dt_to_work.strftime('%Y-%m-%dT%H:%M:%S')
str_to_home = dt_to_home.strftime('%Y-%m-%dT%H:%M:%S')


# ==========================================
# --- 3. 통신용 핵심 함수 정의 ---
# ==========================================

# [Naver] 주소 -> 좌표 변환
def get_naver_geocode(address):
    if pd.isna(address): return None
    url = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
    try:
        res = requests.get(url, headers=NAVER_HEADERS, params={"query": str(address)})
        if res.status_code == 200:
            data = res.json()
            if data.get('addresses'):
                return f"{data['addresses'][0]['x']},{data['addresses'][0]['y']}"  # "경도,위도"
    except Exception as e:
        print(f"네이버 지오코딩 오류 ({address}): {e}")
    return None


# [Naver] 운전 소요시간 계산
def get_naver_driving_time(start_coord, goal_coord, departure_time):
    if not start_coord or not goal_coord: return None
    url = "https://maps.apigw.ntruss.com/map-direction/v1/driving"
    params = {"start": start_coord, "goal": goal_coord, "option": "trafast", "departureTime": departure_time}
    try:
        res = requests.get(url, headers=NAVER_HEADERS, params=params)
        if res.status_code == 200:
            data = res.json()
            if 'route' in data and 'trafast' in data['route']:
                duration_ms = data['route']['trafast'][0]['summary']['duration']
                return round(duration_ms / 1000 / 60)  # 분 단위 변환
    except Exception as e:
        print(f"네이버 길찾기 오류: {e}")
    return None


# [Google] 대중교통 소요시간 계산
def get_google_transit_time(origin, destination, departure_time):
    if pd.isna(origin) or pd.isna(destination): return None
    try:
        result = gmaps.distance_matrix(
            origins=str(origin), destinations=str(destination),
            mode="transit", departure_time=departure_time, language="ko"
        )
        if result['status'] == 'OK':
            element = result['rows'][0]['elements'][0]
            if element['status'] == 'OK':
                duration_sec = element['duration']['value']
                return round(duration_sec / 60)  # 분 단위 변환
    except Exception as e:
        print(f"구글 길찾기 오류 ({origin}): {e}")
    return None


# ==========================================
# --- 4. 데이터 로드 및 분석 수행 ---
# ==========================================
print("데이터를 불러오고 API 분석을 준비합니다...\n")
df = pd.read_excel(file_path)

# 네이버 API용 회사 좌표 미리 확보 (구글은 텍스트 그대로 사용)
naver_company_coord = get_naver_geocode(COMPANY_ADDRESS)
if not naver_company_coord:
    print("❌ 네이버 API: 회사의 위치 좌표를 찾을 수 없습니다. API 상태를 확인해 주세요.")
    exit()

print(f"🏢 회사 주소 및 좌표 셋업 완료: {COMPANY_ADDRESS}")
print(f"👥 전체 직원 수: {len(df)}명 (Naver/Google 분기 처리 시작)\n")

to_work_times = []
to_home_times = []
total_times = []
used_apis = []  # 어떤 API를 썼는지 로깅용

# 루프 돌면서 gtw 조건에 따라 API 분기 처리
for idx, row in df.iterrows():
    address = row['address']
    gtw = str(row['gtw']).strip().lower()

    t_work, t_home = None, None
    api_used = "N/A"

    # --- 자차 출퇴근 (Naver) ---
    if gtw == 'driving':
        api_used = "Naver (Driving)"
        home_coord = get_naver_geocode(address)
        if home_coord:
            t_work = get_naver_driving_time(home_coord, naver_company_coord, str_to_work)
            t_home = get_naver_driving_time(naver_company_coord, home_coord, str_to_home)

    # --- 대중교통 출퇴근 (Google) ---
    elif gtw == 'transit':
        api_used = "Google (Transit)"
        t_work = get_google_transit_time(address, COMPANY_ADDRESS, dt_to_work)
        t_home = get_google_transit_time(COMPANY_ADDRESS, address, dt_to_home)

    # 합계 계산
    if t_work is not None and t_home is not None:
        t_total = t_work + t_home
    else:
        t_total = None

    to_work_times.append(t_work)
    to_home_times.append(t_home)
    total_times.append(t_total)
    used_apis.append(api_used)

    # 진행 상황 출력 (10건마다)
    if (idx + 1) % 10 == 0 or (idx + 1) == len(df):
        print(f"  -> {idx + 1} / {len(df)}명 처리 완료...")

# ==========================================
# --- 5. 결과 통합 및 저장 ---
# ==========================================
# 데이터프레임에 파생 변수 추가
df['출근_소요시간(분)'] = to_work_times
df['퇴근_소요시간(분)'] = to_home_times
df['총_소요시간(분)'] = total_times
df['분석_사용API'] = used_apis

# 엑셀 파일로 저장
df.to_excel(output_path, index=False)

print("\n" + "=" * 60)
print(f"✅ 네이버(운전) & 구글(대중교통) 통합 소요시간 계산이 완료되었습니다.")
print(f"💾 저장 경로: {output_path}")
print("=" * 60)