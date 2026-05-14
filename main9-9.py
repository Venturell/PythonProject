import pandas as pd
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import re
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 환경 설정 및 상수 정의
# ==========================================
CSV_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#9\9_PAproject_9_4_sentiment.csv"
OUTPUT_PATH = os.path.join(os.path.dirname(CSV_PATH), "9_toxicity_results.csv")
MODEL_NAME = "beomi/korean-hatespeech-classifier"


class ToxicityAnalyzer:
    def __init__(self, model_name):
        self.model_name = model_name
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = None
        self.model = None

        # 라벨 매핑 (모델 출력 인덱스 기준: 보통 0=none, 1=offensive, 2=hate)
        # ※ 모델의 학습 데이터(BEEP 등)에 따라 다를 수 있으나 보편적인 매핑 사용
        self.label_map = {
            'none': ('정상', '✅', False),
            'offensive': ('공격적', '⚠️', True),
            'hate': ('혐오', '🚨', True)
        }

    def step1_load_model(self):
        print(f"[Step 1] 모델 로드 중... ({self.model_name})")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()
        print(f"  -> 완료 (사용 장치: {self.device})")

    def step2_preprocess_text(self, text):
        """한글과 공백을 제외한 특수문자 제거"""
        if pd.isna(text):
            return ""
        # 한글(초성/중성/종성)과 공백만 남기고 모두 제거
        clean_text = re.sub(r'[^가-힣ㄱ-ㅎㅏ-ㅣ\s]', '', str(text))
        return clean_text.strip()

    def _get_mapped_label(self, model_label):
        """모델의 원본 라벨을 한글 라벨과 이모지로 변환"""
        label_lower = str(model_label).lower()
        if 'none' in label_lower or '0' in label_lower:
            return self.label_map['none']
        elif 'offensive' in label_lower or '1' in label_lower:
            return self.label_map['offensive']
        elif 'hate' in label_lower or '2' in label_lower:
            return self.label_map['hate']
        else:
            return self.label_map['none']  # Fallback

    def step3_analyze_data(self, df):
        print("\n[Step 3] 데이터 전처리 및 독성 분석 진행 중...")

        results = []
        total = len(df)

        with torch.no_grad():
            for idx, row in df.iterrows():
                original_text = row['review']
                clean_text = self.step2_preprocess_text(original_text)

                # 전처리 후 텍스트가 비어있으면 정상 처리
                if not clean_text:
                    results.append({'정상_확률': 100.0, '공격적_확률': 0.0, '혐오_확률': 0.0,
                                    'toxicity_label': '정상 ✅', 'is_toxic': False})
                    continue

                # 토큰화 및 예측
                inputs = self.tokenizer(clean_text, return_tensors="pt", truncation=True, max_length=128).to(
                    self.device)
                outputs = self.model(**inputs)
                probs = F.softmax(outputs.logits, dim=1).squeeze().cpu().numpy()

                # 라벨 추출
                id2label = self.model.config.id2label
                pred_idx = probs.argmax()
                raw_label = id2label[pred_idx]

                # 커스텀 매핑 적용
                korean_label, emoji, is_toxic = self._get_mapped_label(raw_label)

                # 확률 점수 정리 (일반적으로 0:none, 1:offensive, 2:hate 구조로 가정)
                # 모델 구조에 따라 인덱스가 다를 수 있으나 범용적으로 확률 배열 매핑
                score_dict = {}
                for i, prob in enumerate(probs):
                    lbl_name = self._get_mapped_label(id2label[i])[0]
                    score_dict[f'{lbl_name}_확률'] = round(prob * 100, 2)

                row_result = {
                    **score_dict,
                    'toxicity_label': f"{korean_label} {emoji}",
                    'is_toxic': is_toxic
                }
                results.append(row_result)

                if (idx + 1) % 50 == 0 or (idx + 1) == total:
                    print(f"  -> {idx + 1} / {total}건 분석 완료")

        # 결과를 원본 데이터프레임과 병합
        result_df = pd.DataFrame(results)
        return pd.concat([df.reset_index(drop=True), result_df], axis=1)

    def step4_generate_report(self, analyzed_df):
        print("\n[Step 4] 📊 분석 리포트 요약")
        print("=" * 60)

        # 1) 전체 데이터 독성 분포 (빈도수 및 백분율)
        label_counts = analyzed_df['toxicity_label'].value_counts()
        total = len(analyzed_df)

        print(f"총 리뷰 수: {total}건")
        print("-" * 60)

        for label, count in label_counts.items():
            pct = (count / total) * 100
            # ASCII 막대 그래프 (2%당 1칸)
            bar_length = int(pct / 2)
            bar = '█' * bar_length
            print(f"{label:<8} | {count:4d}건 ({pct:5.1f}%) | {bar}")

        print("=" * 60)

        # 2) 독성(is_toxic == True)으로 판정된 리뷰 리스트업
        toxic_reviews = analyzed_df[analyzed_df['is_toxic'] == True]
        print(f"\n🚨 [주의] 독성(공격적/혐오)으로 판별된 리뷰 목록 (총 {len(toxic_reviews)}건)")
        print("-" * 60)

        if len(toxic_reviews) > 0:
            for idx, row in toxic_reviews.iterrows():
                print(f"[{row['toxicity_label']}] {row['review']}")
        else:
            print("독성 리뷰가 발견되지 않았습니다. 쾌적한 커뮤니케이션 환경입니다! ✨")
        print("=" * 60)

    def step5_save_data(self, analyzed_df, output_path):
        print(f"\n[Step 5] 분석 결과 저장 중...")
        analyzed_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"  -> 저장 완료! 경로: {output_path}")


# ==========================================
# 메인 실행부
# ==========================================
def main():
    # 데이터 로드 (에러 방지를 위한 다중 인코딩 시도)
    print("[Step 0] 데이터 불러오기")
    try:
        df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    except UnicodeDecodeError:
        df = pd.read_csv(CSV_PATH, encoding='cp949')
    print(f"  -> {len(df)}건의 데이터 로드 완료\n")

    # 분석기 인스턴스 생성 및 파이프라인 실행
    analyzer = ToxicityAnalyzer(MODEL_NAME)

    analyzer.step1_load_model()
    analyzed_df = analyzer.step3_analyze_data(df)
    analyzer.step4_generate_report(analyzed_df)
    analyzer.step5_save_data(analyzed_df, OUTPUT_PATH)


if __name__ == "__main__":
    main()