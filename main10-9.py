import pandas as pd
import requests
import googlemaps
import datetime
import os
import warnings

warnings.filterwarnings('ignore')

#직원들의집을구글맵/네이버맵으로지오코딩-최적지점배치
# ==========================================
# --- 1. API 키 및 지점(Branch) 설정 ---
# ==========================================
# 🚨 본인의 API 키를 정확히 입력하세요.
NAVER_CLIENT_ID = "네이버id"
NAVER_CLIENT_SECRET = "시크릿"
GOOGLE_API_KEY = "구글api키입력"

NAVER_HEADERS = {
    "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
    "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
}
gmaps = googlemaps.Client(key=GOOGLE_API_KEY)

# 회사 지점 리스트
branches = {
    "지점1(강남)": "서울특별시 강남구 테헤란로 231",
    "지점2(종로)": "서울특별시 종로구 세종대로 209",
    "지점3(용산)": "서울특별시 용산구 원효로 216"
}

# 파일 경로
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#10\10_PAproject_10_3_Address.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "10_PAproject_10_3_Optimal_Branch.xlsx")

# ==========================================
# --- 2. 출퇴근 시간 기준 설정 (가장 가까운 평일) ---
# ==========================================
now = datetime.datetime.now()
days_ahead = 0 if now.weekday() < 5 else (7 - now.weekday())
target_date = now + datetime.timedelta(days=days_ahead)

# 07:30 (출근), 18:30 (퇴근)
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
        pass
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
        pass
    return None


def get_google_transit_time(origin, destination, departure_time):
    if pd.isna(origin) or pd.isna(destination): return None
    try:
        result = gmaps.distance_matrix(
            origins=str(origin), destinations=str(destination),
            mode="transit", departure_time=departure_time, language="ko"
        )
        if result['status'] == 'OK' and result['rows'][0]['elements'][0]['status'] == 'OK':
            return round(result['rows'][0]['elements'][0]['duration']['value'] / 60)
    except Exception as e:
        pass
    return None


# ==========================================
# --- 4. 데이터 로드 및 최적 지점 분석 수행 ---
# ==========================================
print("데이터를 로드하고 지점별 분석을 시작합니다...\n")
df = pd.read_excel(file_path)

# 네이버 지오코딩 속도 향상을 위해 지점별 좌표 미리 캐싱
naver_branch_coords = {}
for b_name, b_addr in branches.items():
    coord = get_naver_geocode(b_addr)
    if coord:
        naver_branch_coords[b_name] = coord

# 결과를 담을 딕셔너리 리스트
results_list = []

for idx, row in df.iterrows():
    home_address = row['address']
    gtw = str(row['gtw']).strip().lower()

    # 직원별 결과를 담을 임시 딕셔너리
    emp_result = {
        'address': home_address,
        'gtw': gtw
    }

    # 자차 이용자(driving)를 위해 집 좌표 한 번만 추출
    home_coord = None
    if gtw == 'driving':
        home_coord = get_naver_geocode(home_address)

    # 지점별 시간 총합을 비교하기 위한 변수
    totals_dict = {}

    # 3개 지점을 순회하며 계산
    for b_name, b_addr in branches.items():
        t_work, t_home, t_total = None, None, None

        # 1) 자차 출퇴근 (Naver)
        if gtw == 'driving' and home_coord and (b_name in naver_branch_coords):
            comp_coord = naver_branch_coords[b_name]
            t_work = get_naver_driving_time(home_coord, comp_coord, str_to_work)
            t_home = get_naver_driving_time(comp_coord, home_coord, str_to_home)

        # 2) 대중교통 출퇴근 (Google)
        elif gtw == 'transit':
            t_work = get_google_transit_time(home_address, b_addr, dt_to_work)
            t_home = get_google_transit_time(b_addr, home_address, dt_to_home)

        # 총합 계산
        if t_work is not None and t_home is not None:
            t_total = t_work + t_home
            totals_dict[b_name] = t_total

        # 결과 저장
        emp_result[f'{b_name}_출근(분)'] = t_work
        emp_result[f'{b_name}_퇴근(분)'] = t_home
        emp_result[f'{b_name}_총합(분)'] = t_total

    # --- 직원별 최적 지점 찾기 ---
    best_branch = None
    min_time = None

    # 계산된 총합(totals_dict)이 존재할 경우 최소값을 가진 지점 추출
    if totals_dict:
        best_branch = min(totals_dict, key=totals_dict.get)
        min_time = totals_dict[best_branch]

    emp_result['최적_배치_지점'] = best_branch
    emp_result['최적_소요시간(분)'] = min_time

    results_list.append(emp_result)

    if (idx + 1) % 10 == 0 or (idx + 1) == len(df):
        print(f"  -> {idx + 1} / {len(df)}명 분석 완료...")

# ==========================================
# --- 5. 최종 엑셀 병합 및 저장 ---
# ==========================================
# 직원별 계산 결과를 데이터프레임으로 변환
df_calculated = pd.DataFrame(results_list)

# 원본 데이터와 병합 (기존 변수 유지 + 계산된 컬럼 11개 추가)
df_final = df.merge(
    df_calculated.drop(columns=['address', 'gtw']),
    left_index=True,
    right_index=True,
    how='left'
)

# 엑셀 파일로 저장
df_final.to_excel(output_path, index=False)

# 결과 요약 리포트
branch_counts = df_final['최적_배치_지점'].value_counts()
print("\n" + "=" * 60)
print("🎯 [직원별 최적 지점 배치 시뮬레이션 결과]")
print("=" * 60)
print(f"💾 엑셀 저장 경로: {output_path}\n")
print("[각 지점별 최적 할당 인원 요약]")
for branch_name, count in branch_counts.items():
    print(f"- {branch_name} : {count}명 배치 추천")
print("=" * 60)