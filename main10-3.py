import pandas as pd
import requests
import folium
import os
import warnings

warnings.filterwarnings('ignore')

#직원들의집을네이버맵으로지오코딩
# ==========================================
# --- 1. API 키 및 설정 ---
# ==========================================
# 🚨 본인의 네이버 클라우드 플랫폼 API 키를 입력하세요.
NAVER_CLIENT_ID = "여기에_Client_ID_입력"
NAVER_CLIENT_SECRET = "여기에_Client_Secret_입력"

# ==========================================
# --- 2. 파일 경로 설정 ---
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#10\10_PAproject_10_3_Address.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "10_PAproject_10_3_Map.html")

print("데이터를 불러오고 주소를 좌표로 변환합니다. (데이터 양에 따라 시간이 소요될 수 있습니다.)\n")

# ==========================================
# --- 3. 데이터 로드 및 전처리 ---
# ==========================================
df = pd.read_excel(file_path)


# ==========================================
# --- 4. 지오코딩(주소 -> 좌표 변환) 함수 ---
# ==========================================
def get_lat_lon(address):
    """네이버 Geocoding API를 사용하여 주소를 위도/경도로 변환"""
    if pd.isna(address):
        return None, None

    url = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    params = {"query": str(address)}

    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            data = res.json()
            if data['addresses']:  # 변환 결과가 존재하는 경우
                lon = float(data['addresses'][0]['x'])  # 경도
                lat = float(data['addresses'][0]['y'])  # 위도
                return lat, lon
    except Exception as e:
        print(f"주소 변환 중 오류 발생 ({address}): {e}")

    return None, None


# ==========================================
# --- 5. 마커 색상 결정 함수 ---
# ==========================================
def get_marker_color(gender, children):
    """성별과 자녀 유무에 따른 마커 색상 반환"""
    if gender == '여' and children == '유':
        return 'red'
    elif gender == '여' and children == '무':
        return 'green'
    elif gender == '남' and children == '유':
        return 'blue'
    elif gender == '남' and children == '무':
        return 'purple'
    else:
        return 'gray'  # 조건에 맞지 않거나 결측치인 경우


# ==========================================
# --- 6. 좌표 변환 및 지도 시각화 ---
# ==========================================
def main():
    lats = []
    lons = []

    # 주소를 순회하며 좌표 변환
    for idx, row in df.iterrows():
        lat, lon = get_lat_lon(row['address'])
        lats.append(lat)
        lons.append(lon)

        # 진행 상황 출력 (50건마다)
        if (idx + 1) % 50 == 0:
            print(f"  -> {idx + 1}건 변환 완료...")

    df['latitude'] = lats
    df['longitude'] = lons

    # 좌표 변환에 성공한 데이터만 필터링
    df_valid = df.dropna(subset=['latitude', 'longitude'])

    if df_valid.empty:
        print("\n❌ 변환된 좌표가 없습니다. API 키와 주소 데이터를 확인해 주세요.")
        return

    # 지도의 초기 중심점을 직원 거주지들의 평균 좌표로 설정
    center_lat = df_valid['latitude'].mean()
    center_lon = df_valid['longitude'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

    # 맵에 마커 추가
    for idx, row in df_valid.iterrows():
        color = get_marker_color(row['gender'], row['children'])

        # 마커 클릭 시 팝업으로 보여줄 직원 정보 구성
        popup_text = f"""
        <b>[직원 정보]</b><br>
        - 성별: {row['gender']}<br>
        - 자녀: {row['children']}<br>
        - 나이: {row.get('age', 'N/A')}<br>
        - 근속연수: {row.get('tenure', 'N/A')}
        """

        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_text, max_width=250),
            icon=folium.Icon(color=color, icon='user')
        ).add_to(m)

    # HTML 파일로 최종 저장
    m.save(output_path)

    print("\n" + "=" * 60)
    print(f"✅ 총 {len(df_valid)}건의 지도 시각화가 완료되었습니다.")
    print(f"💾 저장 경로: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()