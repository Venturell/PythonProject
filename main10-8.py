import pandas as pd
import requests
import googlemaps
import datetime
import os
import warnings

warnings.filterwarnings('ignore')

#직원들의집을구글맵/네이버맵으로지오코딩-최적본사위치
# ==========================================
# --- 1. API 키 및 후보지 설정 ---
# ==========================================
# 🚨 본인의 API 키를 정확히 입력하세요.
NAVER_CLIENT_ID = "네이버CLIENTID"
NAVER_CLIENT_SECRET = "네이버CLIENTSECRET"
GOOGLE_API_KEY = "구글API키"

NAVER_HEADERS = {
    "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
    "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
}
gmaps = googlemaps.Client(key=GOOGLE_API_KEY)

# 이전 후보지 리스트
candidates = {
    "후보1_강남": "서울특별시 강남구 테헤란로 231",
    "후보2_종로": "서울특별시 종로구 세종대로 209",
    "후보3_용산": "서울특별시 용산구 원효로 216"
}

# 파일 경로 및 출력 경로 설정
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#10\10_PAproject_10_3_Address.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "10_PAproject_10_3_Relocation_Analysis.xlsx")

# ==========================================
# --- 2. 출퇴근 시간 설정 (평일 기준) ---
# ==========================================
now = datetime.datetime.now()
days_ahead = 0 if now.weekday() < 5 else (7 - now.weekday())
target_date = now + datetime.timedelta(days=days_ahead)

dt_to_work = target_date.replace(hour=7, minute=30, second=0, microsecond=0)
dt_to_home = target_date.replace(hour=18, minute=30, second=0, microsecond=0)

str_to_work = dt_to_work.strftime('%Y-%m-%dT%H:%M:%S')
str_to_home = dt_to_home.strftime('%Y-%m-%dT%H:%M:%S')


# ==========================================
# --- 3. 통신용 핵심 함수 정의 ---
# ==========================================
def get_naver_geocode(address):
    if pd.isna(address): return None
    url = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
    try:
        res = requests.get(url, headers=NAVER_HEADERS, params={"query": str(address)})
        if res.status_code == 200:
            data = res.json()
            if data.get('addresses'):
                return f"{data['addresses'][0]['x']},{data['addresses'][0]['y']}"
    except Exception as e:
        print(f"네이버 지오코딩 오류 ({address}): {e}")
    return None


def get_naver_driving_time(start_coord, goal_coord, departure_time):
    if not start_coord or not goal_coord: return None
    url = "https://maps.apigw.ntruss.com/map-direction/v1/driving"
    params = {"start": start_coord, "goal": goal_coord, "option": "trafast", "departureTime": departure_time}
    try:
        res = requests.get(url, headers=NAVER_HEADERS, params=params)
        if res.status_code == 200:
            data = res.json()
            if 'route' in data and 'trafast' in data['route']:
                return round(data['route']['trafast'][0]['summary']['duration'] / 1000 / 60)
    except Exception as e:
        print(f"네이버 길찾기 오류: {e}")
    return None


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
                return round(element['duration']['value'] / 60)
    except Exception as e:
        print(f"구글 길찾기 오류 ({origin}): {e}")
    return None


# ==========================================
# --- 4. 후보지별 순회 분석 실행 ---
# ==========================================
print("💾 데이터를 로드하고 후보지별 통근 거리 및 시간 최적화 분석을 시작합니다.")
df = pd.read_excel(file_path)

# 후보지별 네이버 좌표 매핑 사전 준비
naver_candidate_coords = {}
for name, addr in candidates.items():
    coord = get_geocode_coord = get_naver_geocode(addr)
    if coord:
        naver_candidate_coords[name] = coord

# 최종 결과를 누적할 데이터프레임 복사본 생성
df_result = df.copy()
candidate_totals = {}

for c_id, (c_name, c_address) in enumerate(candidates.items(), 1):
    print(f"\n🏢 [후보 {c_id}] {c_name} 분석 중... ({c_address})")

    to_work_list, to_home_list, total_list = [], [], []

    for idx, row in df.iterrows():
        home_address = row['address']
        gtw = str(row['gtw']).strip().lower()

        t_work, t_home = None, None

        if gtw == 'driving':
            home_coord = get_naver_geocode(home_address)
            comp_coord = naver_candidate_coords.get(c_name)
            if home_coord and comp_coord:
                t_work = get_naver_driving_time(home_coord, comp_coord, str_to_work)
                t_home = get_naver_driving_time(comp_coord, home_coord, str_to_home)

        elif gtw == 'transit':
            t_work = get_google_transit_time(home_address, c_address, dt_to_work)
            t_home = get_google_transit_time(c_address, home_address, dt_to_home)

        t_total = (t_work + t_home) if (t_work is not None and t_home is not None) else None

        to_work_list.append(t_work)
        to_home_list.append(t_home)
        total_list.append(t_total)

    # 결과 컬럼 동적 추가
    df_result[f'{c_name}_출근(분)'] = to_work_list
    df_result[f'{c_name}_퇴근(분)'] = to_home_list
    df_result[f'{c_name}_총합(분)'] = total_list

    # 해당 후보지의 전체 직원 시간 총합 계산 (결측치 제외)
    total_sum = pd.Series(total_list).sum(skipna=True)
    candidate_totals[c_name] = total_sum
    print(f"  -> 전직원 출퇴근 시간 총합: {total_sum:,} 분")

# ==========================================
# --- 5. 최적 후보지 산출 및 저장 ---
# ==========================================
best_candidate = min(candidate_totals, key=candidate_totals.get)

print("\n" + "=" * 60)
print("📊 [오피스 이전 후보지 최적화 최종 분석 결과]")
print("=" * 60)
for name, total_val in candidate_totals.items():
    print(f"- {name}: 총 {total_val:,} 분 (약 {round(total_val / 60, 1)} 시간)")
print("-" * 60)
print(f"🎯 최적의 오피스 이전 후보지는 [{best_candidate}] 입니다.")
print("=" * 60)

# 엑셀 파일로 세부 데이터 저장
df_result.to_excel(output_path, index=False)
print(f"\n💾 세부 분석 결과가 엑셀 파일로 저장되었습니다.\n경로: {output_path}")