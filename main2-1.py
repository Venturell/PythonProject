import os
import time
import urllib.request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 1 & 2. 수정된 네이버 이미지 검색 주소 적용 ('보넥도 성호' 검색 결과)
url = "https://search.naver.com/search.naver?ssc=tab.image.all&where=image&sm=tab_jum&query=%EB%B3%B4%EB%84%A5%EB%8F%84+%EC%84%B1%ED%98%B8"

# 3. 지정된 저장 경로 설정
save_path = r'C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#1\1'

# 저장할 폴더가 없다면 새로 생성
if not os.path.exists(save_path):
    os.makedirs(save_path)
    print(f"저장 폴더가 존재하지 않아 새로 생성했습니다:\n{save_path}")

# 4. selenium webdriver manager를 이용한 크롬 브라우저 자동 설정
print("웹 브라우저를 열고 있습니다...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

try:
    # 설정한 주소로 이동
    driver.get(url)

    # 이미지가 로딩될 수 있도록 3초 대기
    time.sleep(3)

    # 더 많은 이미지가 로딩되도록 스크롤을 살짝 내립니다
    driver.execute_script("window.scrollTo(0, 1000);")
    time.sleep(2)

    # 네이버 이미지 썸네일 요소 찾기
    images = driver.find_elements(By.CSS_SELECTOR, "img._image, img._fe_image_tab_content_thumbnail_image")

    print(f"이미지 탐색 완료. 다운로드를 시작합니다.")

    count = 1
    for img in images:
        if count > 20:  # 5. 정확히 20장만 다운로드하고 종료
            break

        src = img.get_attribute('src')

        # 이미지 주소(src)가 정상적인 웹 링크(http)인 경우에만 다운로드
        if src and src.startswith("http"):
            # 파일명 지정: SH1.jpg, SH2.jpg ... SH20.jpg
            file_name = f"SH{count}.jpg"
            file_path = os.path.join(save_path, file_name)

            try:
                # 썸네일 이미지 다운로드
                urllib.request.urlretrieve(src, file_path)
                print(f"[{count}/20] {file_name} 저장 완료")
                count += 1
            except Exception as e:
                print(f"{count}번째 이미지 저장 실패: {e}")

    print(f"\n🎉 20장 다운로드가 모두 완료되었습니다! 폴더를 확인해 보세요.")

except Exception as e:
    print(f"실행 중 오류가 발생했습니다: {e}")

finally:
    # 작업이 끝나면 크롬 브라우저 종료
    driver.quit()