import requests
import pandas as pd

# 1. 발급받으신 API 키를 입력하세요
API_KEY = '5ae1c23e0d9aa0bf8cc36e43414d8d22c11c4d2e'

# 테스트용 변수 (삼성전자 고유번호, 2023년 사업보고서)
corp_code = '00126380' # DART 고유번호
bsns_year = '2023'     # 사업연도 [cite: 175]
reprt_code = '11011'   # 보고서 코드 (11011: 사업보고서) [cite: 175]

def get_employee_data(api_key, corp_code, bsns_year, reprt_code):
    """사업보고서 내 직원현황 데이터 수집"""
    url = 'https://opendart.fss.or.kr/api/empSttus.json' # 직원현황 API [cite: 137]
    params = {
        'crtfc_key': api_key,
        'corp_code': corp_code,
        'bsns_year': bsns_year,
        'reprt_code': reprt_code
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == '000':
            return pd.DataFrame(data['list'])
        else:
            print(f"직원현황 에러: {data.get('message')}")
    return None

def get_financial_data(api_key, corp_code, bsns_year, reprt_code):
    """단일회사 주요계정(재무정보) 데이터 수집"""
    url = 'https://opendart.fss.or.kr/api/fnlttSinglAcnt.json' # 재무정보 API [cite: 138]
    params = {
        'crtfc_key': api_key,
        'corp_code': corp_code,
        'bsns_year': bsns_year,
        'reprt_code': reprt_code
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == '000':
            return pd.DataFrame(data['list'])
        else:
            print(f"재무정보 에러: {data.get('message')}")
    return None

# 실행 테스트
print("데이터 수집 중...")
emp_df = get_employee_data(API_KEY, corp_code, bsns_year, reprt_code)
fin_df = get_financial_data(API_KEY, corp_code, bsns_year, reprt_code)

print("\n--- 직원 현황 ---")
if emp_df is not None:
    # 1인평균 급여액, 평균 근속 연수 등 확인 [cite: 157]
    print(emp_df[['corp_name', 'avrg_cnwk_sdytrn', 'jan_salary_am', 'sm']].head())

print("\n--- 주요 재무정보 ---")
if fin_df is not None:
    # 매출액, 영업이익, 자산총계 등 확인 [cite: 161]
    print(fin_df[['account_nm', 'thstrm_amount']].head())