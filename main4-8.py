import requests
import xml.etree.ElementTree as ET
import pandas as pd


def get_enterprise_salary(year, service_key):
    """특정 연도의 기관별 신입사원 평균연봉 데이터를 가져와 데이터프레임으로 반환"""
    url = 'http://apis.data.go.kr/B551982/openApiNewAverPay/openXmlNewAverPay'
    params = {
        'serviceKey': service_key,
        'pageNo': '1',
        'numOfRows': '500',
        'ac_year': str(year),
        'type': 'xml'
    }

    try:
        response = requests.get(url, params=params)
        response.encoding = 'utf-8'
        root = ET.fromstring(response.text)

        data = []
        for item in root.findall('.//item'):
            ent_name = item.findtext('ENT_NAME')
            n_sum_str = item.findtext('N_SUM')

            if ent_name and n_sum_str:
                try:
                    # 콤마 제거 및 소수점 처리 후 정수 변환
                    clean_val = int(n_sum_str.replace(',', '').split('.')[0])
                    data.append({'기관명': ent_name, f'연봉_{year}': clean_val})
                except ValueError:
                    continue
        return pd.DataFrame(data)
    except Exception as e:
        print(f"{year}년 데이터 호출 중 오류 발생: {e}")
        return pd.DataFrame()


# 1. 인증키 설정
service_key = '6df9b430ab949ce84679b7f87cf1c4b6474c0f54ef67e825b4ad454e993bf000'

# 2. 2023년 및 2024년 데이터 각각 호출
print("2023년 데이터를 불러오는 중...")
df_2023 = get_enterprise_salary(2023, service_key)

print("2024년 데이터를 불러오는 중...")
df_2024 = get_enterprise_salary(2024, service_key)

# 3. 데이터 분석 진행
if not df_2023.empty and not df_2024.empty:
    # '기관명'을 기준으로 두 데이터 병합 (두 연도 모두 데이터가 있는 기관만 대상)
    df_merged = pd.merge(df_2023, df_2024, on='기관명', how='inner')

    # 상승액 계산 (단위: 천원)
    df_merged['상승액'] = df_merged['연봉_2024'] - df_merged['연봉_2023']

    # 상승액 기준 내림차순 정렬
    df_result = df_merged.sort_values(by='상승액', ascending=False)

    # 상위 20개 기업 추출
    top20_increase = df_result.head(20).copy()

    # 가독성을 위해 단위를 '만원'으로 변경
    top20_increase['상승액(만원)'] = (top20_increase['상승액'] / 10).astype(int)
    top20_increase['24년연봉(만원)'] = (top20_increase['연봉_2024'] / 10).astype(int)

    # 순위 설정 및 출력 컬럼 정리
    top20_increase.index = range(1, len(top20_increase) + 1)
    final_report = top20_increase[['기관명', '24년연봉(만원)', '상승액(만원)']]

    print("\n" + "=" * 60)
    print("📈 2023년 대비 2024년 신입사원 연봉 상승 Top 20 📈")
    print("=" * 60)
    if not final_report.empty:
        print(final_report.to_string())
    else:
        print("비교 가능한 데이터가 충분하지 않습니다.")
    print("=" * 60)
else:
    print("데이터 호출에 실패하여 분석을 진행할 수 없습니다.")