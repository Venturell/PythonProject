import requests
import xml.etree.ElementTree as ET
import pandas as pd

# 1. API 주소 및 인증키
url = 'http://apis.data.go.kr/B551982/openApiNewAverPay/openXmlNewAverPay'
service_key = '6df9b430ab949ce84679b7f87cf1c4b6474c0f54ef67e825b4ad454e993bf000'

params = {
    'serviceKey': service_key,
    'pageNo': '1',
    'numOfRows': '500',  # 넉넉하게 500개로 늘렸습니다.
    'ac_year': '2024',
    'type': 'xml'
}

print("2024년 데이터를 다시 꼼꼼하게 분석 중입니다...")

try:
    response = requests.get(url, params=params)
    response.encoding = 'utf-8'
    xml_data = response.text

    root = ET.fromstring(xml_data)
    result_code = root.findtext('.//resultCode')

    if result_code in ['00', '0']:
        data_list = []

        # 💡 개선점 1: 서버에서 데이터를 몇 개 가져왔는지부터 확인합니다.
        items = root.findall('.//item')
        print(f"👉 서버 응답 성공! 총 {len(items)}개의 기업 데이터를 찾았습니다.\n")

        for item in items:
            ent_name = item.findtext('ENT_NAME')
            n_sum_str = item.findtext('N_SUM')

            if ent_name and n_sum_str:
                try:
                    # 💡 개선점 2: 문자열에 콤마(,)나 소수점이 섞여 있어도 강제로 제거하고 순수 숫자로 만듭니다.
                    clean_sum_str = n_sum_str.replace(',', '').split('.')[0]
                    n_sum = int(clean_sum_str)

                    data_list.append({
                        '기관명': ent_name,
                        '신입사원 평균연봉(천원)': n_sum
                    })
                except ValueError:
                    print(f"[{ent_name}] 연봉 데이터 형식 오류로 제외됨: {n_sum_str}")
                    continue

        df = pd.DataFrame(data_list)

        if not df.empty:
            df_sorted = df.sort_values(by='신입사원 평균연봉(천원)', ascending=False)
            top20_df = df_sorted.head(20).copy()
            top20_df.index = range(1, len(top20_df) + 1)

            top20_df['신입사원 평균연봉(만원)'] = (top20_df['신입사원 평균연봉(천원)'] / 10).astype(int)
            final_display_df = top20_df[['기관명', '신입사원 평균연봉(만원)']]

            print("=" * 50)
            print("🏆 2024년 지역공기업 신입사원 평균연봉 Top 20 🏆")
            print("=" * 50)
            print(final_display_df.to_string())
            print("=" * 50)
        else:
            print("데이터를 찾았으나 연봉 숫자를 추출하지 못했습니다.")
            # 어떤 형태로 데이터가 들어왔는지 확인하기 위해 원본 일부를 출력합니다.
            print(f"서버 응답 원본 확인: {xml_data[:500]}")

    else:
        print(f"API 오류 발생: {root.findtext('.//resultMsg')}")

except Exception as e:
    print(f"오류가 발생했습니다: {e}")