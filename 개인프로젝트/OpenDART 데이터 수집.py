import os
import requests
import pandas as pd
import time
import zipfile
import io
import xml.etree.ElementTree as ET
from tqdm import tqdm

# =========================================================================
# 1. 사용자 설정 항목
# =========================================================================
API_KEY = '5ae1c23e0d9aa0bf8cc36e43414d8d22c11c4d2e'
SAVE_DIR = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\개인프로젝트"

YEARS = ['2020', '2021', '2022', '2023', '2024']  # 분석 기간: 최근 5개년
REPRT_CODE = '11011'  # 11011: 사업보고서

if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)


# =========================================================================
# 2. OpenDART API 수집 함수
# =========================================================================
def get_listed_corps(api_key):
    """주식종목코드가 존재하는 실제 상장사만 필터링하여 목록을 반환합니다."""
    url = 'https://opendart.fss.or.kr/api/corpCode.xml'
    response = requests.get(url, params={'crtfc_key': api_key})

    z = zipfile.ZipFile(io.BytesIO(response.content))
    xml_data = z.read('CORPCODE.xml')
    tree = ET.fromstring(xml_data)

    corp_list = []
    for list_node in tree.findall('list'):
        stock_code = list_node.find('stock_code').text
        if stock_code is not None and stock_code.strip() != '':
            corp_list.append({
                'corp_code': list_node.find('corp_code').text,
                'corp_name': list_node.find('corp_name').text,
                'stock_code': stock_code
            })
    return pd.DataFrame(corp_list)


def get_dart_data(url, api_key, corp_code, year):
    params = {
        'crtfc_key': api_key,
        'corp_code': corp_code,
        'bsns_year': year,
        'reprt_code': REPRT_CODE
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == '000':
                return pd.DataFrame(data['list'])
    except Exception:
        pass
    return None


# =========================================================================
# 3. 메인 실행 블록 (전체 기업 대상)
# =========================================================================
if __name__ == "__main__":
    print("상장사 목록을 불러오는 중입니다...")
    corps_df = get_listed_corps(API_KEY)

    # [핵심] 슬라이싱 없이 전체 상장사(약 2,500여 개)를 대상으로 실행합니다.
    target_corps = corps_df

    emp_results = []
    fin_results = []

    print(f"총 {len(target_corps)}개 상장기업에 대한 5개년 데이터 수집을 시작합니다.")
    print("데이터가 많아 30분 이상 소요될 수 있습니다. 창을 닫지 마세요!\n")

    for index, row in tqdm(target_corps.iterrows(), total=len(target_corps)):
        corp_code = row['corp_code']
        corp_name = row['corp_name']

        for year in YEARS:
            # 1. 직원 현황
            emp_df = get_dart_data('https://opendart.fss.or.kr/api/empSttus.json', API_KEY, corp_code, year)
            if emp_df is not None and not emp_df.empty:
                emp_df['bsns_year'] = year
                emp_results.append(emp_df)

            # 2. 재무 정보
            fin_df = get_dart_data('https://opendart.fss.or.kr/api/fnlttSinglAcnt.json', API_KEY, corp_code, year)
            if fin_df is not None and not fin_df.empty:
                fin_df['bsns_year'] = year
                fin_df['corp_name'] = corp_name
                fin_results.append(fin_df)

            time.sleep(0.1)  # DART 서버 차단 방지 (필수)

    # =========================================================================
    # 4. 최종 데이터 저장
    # =========================================================================
    print("\n수집 종료! 데이터 병합 및 저장을 시작합니다...")

    if emp_results:
        final_emp_df = pd.concat(emp_results, ignore_index=True)
        emp_save_path = os.path.join(SAVE_DIR, 'employee_data_raw.csv')
        final_emp_df.to_csv(emp_save_path, index=False, encoding='utf-8-sig')
        print(f"✅ 직원 현황 저장 완료: {emp_save_path}")

    if fin_results:
        final_fin_df = pd.concat(fin_results, ignore_index=True)
        fin_save_path = os.path.join(SAVE_DIR, 'financial_data_raw.csv')
        final_fin_df.to_csv(fin_save_path, index=False, encoding='utf-8-sig')
        print(f"✅ 재무 정보 저장 완료: {fin_save_path}")