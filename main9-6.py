import pandas as pd
from soynlp.noun import LRNounExtractor_v2
from soynlp.tokenizer import LTokenizer
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. 데이터 및 불용어 불러오기
# ==========================================
csv_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#9\9_PAproject_9_3_review.csv"
stop_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#9\9_stopwords.txt"

print("데이터를 불러오는 중입니다...")
# CSV 로드 (한글 깨짐 발생 시 encoding='cp949' 로 변경)
df = pd.read_csv(csv_path, encoding='utf-8')
reviews = df['review'].dropna().tolist()

# 불용어 로드 (한글 깨짐 발생 시 encoding='cp949' 로 변경)
with open(stop_path, 'r', encoding='utf-8') as f:
    stopwords = set([line.strip() for line in f.readlines()])

# ==========================================
# 2. soynlp를 활용한 명사 추출 및 토큰화
# ==========================================
print("soynlp를 활용하여 명사를 추출하고 전처리 중입니다...")

# 1) 리뷰 데이터 학습을 통한 명사 추출
noun_extractor = LRNounExtractor_v2(verbose=False)
nouns = noun_extractor.train_extract(reviews)

# 2) 추출된 명사 점수를 바탕으로 토크나이저 생성
noun_scores = {noun: score.score for noun, score in nouns.items()}
tokenizer = LTokenizer(scores=noun_scores)

def process_text(text):
    """
    텍스트를 토큰화한 후,
    1) soynlp가 명사로 인식한 단어만
    2) 불용어 사전에 없는 단어만
    3) 한 글자 이상인 단어만 필터링하여 반환
    """
    tokens = tokenizer.tokenize(text)
    valid_tokens = [
        word for word in tokens
        if word in nouns and word not in stopwords and len(word) > 1
    ]
    return " ".join(valid_tokens)

# 명사만 띄어쓰기로 연결된 텍스트 리스트 생성 (BERTopic의 c-TF-IDF 계산용)
processed_reviews = [process_text(text) for text in reviews]

# ==========================================
# 3. Sentence-Transformers 임베딩
# ==========================================
print("문장 임베딩을 생성 중입니다 (시간이 조금 소요될 수 있습니다)...")
# 지정하신 모델 로드
embedding_model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 💡 핵심 팁: 임베딩은 '문맥'이 살아있는 [원본 리뷰]로 진행해야 Roberta 모델이 의미를 잘 파악합니다.
embeddings = embedding_model.encode(reviews, show_progress_bar=True)

# ==========================================
# 4. BERTopic 모델링 (k=5)
# ==========================================
print("BERTopic 모델링을 진행 중입니다...")

# 전처리된 명사들만 활용하도록 CountVectorizer 설정
vectorizer_model = CountVectorizer()

# 토픽 수(nr_topics)를 5개로 강제 지정
topic_model = BERTopic(
    embedding_model=embedding_model,
    vectorizer_model=vectorizer_model,
    nr_topics=5,
    calculate_probabilities=True
)

# 모델 학습
# 문맥을 파악하는 군집화는 원본 임베딩(embeddings)을, 키워드 추출은 명사만 남긴 데이터(processed_reviews)를 사용
topics, probs = topic_model.fit_transform(processed_reviews, embeddings=embeddings)

# ==========================================
# 5. 결과 확인 및 저장
# ==========================================
print("\n" + "=" * 50)
print("💡 [Topic Modeling 분석 결과]")
print("=" * 50)

# 도출된 토픽들의 정보 출력
topic_info = topic_model.get_topic_info()
print(topic_info)

print("\n[각 토픽별 주요 키워드]")
for topic in range(4): # 0부터 4까지 총 5개 토픽 (혹시 Outlier인 -1 토픽이 있을 수 있음)
    if topic in topic_model.get_topics():
        print(f"Topic {topic}: {topic_model.get_topic(topic)}")

# 필요시 토픽 결과를 원본 데이터프레임에 병합하여 엑셀로 저장 가능
# df['Topic'] = topics
# df.to_excel(r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#9\9_Topic_Result.xlsx", index=False)