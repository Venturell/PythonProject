import time
from google import genai

# 3. API 키 직접 입력 및 클라이언트 생성
api_key = "ThisIsFakeKey"
client = genai.Client(api_key=api_key)

# 1. 분석할 로컬 동영상 파일 경로 설정 (윈도우 경로 오류를 막기 위해 문자열 앞에 r을 붙였습니다)
video_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#1\lee.mp4"

try:
    print("Google AI 서버로 동영상을 업로드하는 중입니다...")
    # 2. google-genai 라이브러리의 files API로 업로드 수행
    video_file = client.files.upload(file=video_path)
    print(f"업로드 완료! (파일 이름: {video_file.name})")

    # 동영상 처리가 끝날 때까지 대기하는 로직
    print("모델이 분석할 수 있도록 동영상을 처리 중입니다", end="")
    while video_file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(3)  # 3초마다 상태 확인
        video_file = client.files.get(name=video_file.name)
    print() # 줄바꿈

    if video_file.state.name == "FAILED":
        raise Exception("동영상 처리에 실패했습니다. 파일이 손상되었거나 지원하지 않는 포맷일 수 있습니다.")

    print("처리 완료! AI 모델에게 행동 분석을 요청합니다...")

    # 4. gemini-2.5-flash 모델을 사용하여 행동 분석 수행
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            video_file,
            "이 동영상의 인물이 어떤 행동을 하고 있는지 구체적으로 분석해 줘. 시간 흐름이나 주요 동작 위주로 설명해 주면 좋아."
        ]
    )

    print("\n================ [ 행동 분석 결과 ] ================\n")
    print(response.text)
    print("\n====================================================\n")

except Exception as e:
    print(f"\n실행 중 오류가 발생했습니다: {e}")