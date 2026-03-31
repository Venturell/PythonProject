import os
import shutil
import re
import numpy as np
import cv2
from insightface.app import FaceAnalysis

# --- 설정 (경로 및 임계값) ---
REF_DIR = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#1\1"
TARGET_DIR = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#1\2"
UNKNOWN_DIR = os.path.join(TARGET_DIR, "unknown")
SIM_THRESHOLD = 0.35
ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png')


# --- 헬퍼 함수 ---
def imread_korean(path):
    """한글 경로가 포함된 이미지를 cv2로 안전하게 읽어오는 함수"""
    try:
        img_array = np.fromfile(path, np.uint8)
        return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"이미지 읽기 오류 ({path}): {e}")
        return None


def get_largest_face(faces):
    """여러 얼굴 중 바운딩 박스 면적이 가장 큰 얼굴을 반환하는 함수"""
    if not faces:
        return None
    # (x2 - x1) * (y2 - y1) 로 면적 계산
    return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))


def extract_normalized_embedding(img_path, app):
    """이미지에서 가장 큰 얼굴의 임베딩을 추출하고 L2 정규화를 수행하는 함수"""
    img = imread_korean(img_path)
    if img is None:
        return None

    faces = app.get(img)
    largest_face = get_largest_face(faces)

    if largest_face is None:
        return None

    emb = largest_face.embedding
    # L2 정규화
    norm = np.linalg.norm(emb)
    if norm == 0:
        return emb
    return emb / norm


# --- 메인 실행 로직 ---
def main():
    print("InsightFace 모델을 로드하는 중입니다. (첫 실행 시 모델 다운로드로 시간이 걸릴 수 있습니다.)")
    # onnxruntime 경고 방지를 위해 CPUExecutionProvider 명시
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))

    # 1. 기준 얼굴(pic\1) 학습 및 임베딩 추출
    print("\n--- 기준 얼굴 학습 시작 ---")
    person_embeddings_raw = {}

    if not os.path.exists(REF_DIR):
        print(f"기준 폴더를 찾을 수 없습니다: {REF_DIR}")
        return

    for filename in os.listdir(REF_DIR):
        if not filename.lower().endswith(ALLOWED_EXTENSIONS):
            continue

        file_path = os.path.join(REF_DIR, filename)

        # 파일명에서 확장자 제거 후 숫자 제거하여 이름(약자) 추출 (예: lh1 -> lh)
        name_only = os.path.splitext(filename)[0]
        person_name = re.sub(r'\d+', '', name_only)

        emb = extract_normalized_embedding(file_path, app)
        if emb is not None:
            if person_name not in person_embeddings_raw:
                person_embeddings_raw[person_name] = []
            person_embeddings_raw[person_name].append(emb)
            print(f"학습 완료: '{filename}' -> 분류 대상: [{person_name}]")
        else:
            print(f"얼굴 검출 실패: '{filename}' (학습 제외)")

    # 사람별로 임베딩 평균을 내고 다시 L2 정규화
    person_avg_embeddings = {}
    for person_name, embs in person_embeddings_raw.items():
        avg_emb = np.mean(embs, axis=0)
        norm = np.linalg.norm(avg_emb)
        if norm != 0:
            avg_emb = avg_emb / norm
        person_avg_embeddings[person_name] = avg_emb

    print(f"\n총 {len(person_avg_embeddings)}명의 기준 얼굴 정보가 평균화되어 준비되었습니다.")

    # unknown 폴더 생성
    if not os.path.exists(UNKNOWN_DIR):
        os.makedirs(UNKNOWN_DIR)

    # 2. 타겟 사진(pic\2) 분류 및 이동
    print("\n--- 사진 분류 및 이동 시작 ---")
    if not os.path.exists(TARGET_DIR):
        print(f"분류할 폴더를 찾을 수 없습니다: {TARGET_DIR}")
        return

    # 타겟 폴더 내의 파일만 읽기 (폴더 제외)
    target_files = [f for f in os.listdir(TARGET_DIR)
                    if os.path.isfile(os.path.join(TARGET_DIR, f)) and f.lower().endswith(ALLOWED_EXTENSIONS)]

    for filename in target_files:
        file_path = os.path.join(TARGET_DIR, filename)

        target_emb = extract_normalized_embedding(file_path, app)

        best_match_name = None
        best_sim = -1.0

        if target_emb is not None:
            # 코사인 유사도 계산: 두 벡터가 L2 정규화되어 있으므로 내적(dot product)이 곧 코사인 유사도입니다.
            for person_name, ref_emb in person_avg_embeddings.items():
                sim = np.dot(target_emb, ref_emb)
                if sim > best_sim:
                    best_sim = sim
                    best_match_name = person_name

        # 임계값 비교 및 이동 경로 설정
        if target_emb is not None and best_sim >= SIM_THRESHOLD:
            dest_dir = os.path.join(TARGET_DIR, best_match_name)
            match_status = f"[{best_match_name}] 일치 (유사도: {best_sim:.4f})"
        else:
            dest_dir = UNKNOWN_DIR
            match_status = f"[unknown] 미달 또는 얼굴 없음 (최대 유사도: {max(best_sim, 0):.4f})"

        # 결과 폴더 생성 및 파일 이동
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        dest_path = os.path.join(dest_dir, filename)

        try:
            shutil.move(file_path, dest_path)
            print(f"이동 완료: {filename} -> {match_status}")
        except Exception as e:
            print(f"파일 이동 실패 ({filename}): {e}")

    print("\n🎉 모든 사진 분류 작업이 완료되었습니다!")


if __name__ == "__main__":
    main()