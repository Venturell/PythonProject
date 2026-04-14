"""
[맞춤형 교육과정 추천 시스템 (Personalized Course Recommender)]
- 목적: 직원 프로필 및 수강 이력을 바탕으로 최적의 교육과정을 추천 (CF, CB, Hybrid 모델 적용)
- 실행 환경: Python 3.x, Windows 로컬 PC, PyCharm IDE
- 필수 패키지 설치 명령어:
  pip install pandas numpy scikit-learn scipy openpyxl
"""

import pandas as pd
import numpy as np
import os
from scipy.sparse.linalg import svds
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
import warnings

warnings.filterwarnings('ignore')

# ══════════════════════════════════════════════════════════════════════════
# 1. 하이퍼파라미터 및 상수 설정
# ══════════════════════════════════════════════════════════════════════════
# 🚨 이전 에러를 방지하기 위해 사용자 PC의 '실제 경로'로 변경해 주세요!
# (예: r"C:\Users\b2209\OneDrive\바탕 화면\박효근\...\6_PAproject_6_4_course.xlsx")
EXCEL_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#6\6_PAproject_6_4_course.xlsx"

TOP_N = 5  # 추천 과목 수
ALPHA = 0.6  # 하이브리드 기본 CF 가중치 (수강 이력에 따라 동적 조정됨)
N_FACTORS = 5  # SVD 잠재 요인 수


# ══════════════════════════════════════════════════════════════════════════
# 2. 데이터 로드 및 전처리 모듈
# ══════════════════════════════════════════════════════════════════════════
def load_excel(path):
    """5개 시트의 존재 여부를 검증하고 데이터를 로드합니다."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"\n[오류] 엑셀 파일을 찾을 수 없습니다.\n설정된 경로를 확인해 주세요: {path}")

    sheets = ['courses', 'employees', 'ratings_train', 'ratings_test', 'recommend_target']
    xls = pd.ExcelFile(path)

    for sheet in sheets:
        if sheet not in xls.sheet_names:
            raise ValueError(f"[오류] 엑셀 파일에 '{sheet}' 시트가 없습니다.")

    data = {sheet: pd.read_excel(xls, sheet_name=sheet) for sheet in sheets}
    print("✅ 데이터 로드 성공 (모든 시트 검증 완료)")
    return data


def build_rating_matrix(ratings_train, employees, courses):
    """직원 × 교육과정 평점 행렬을 생성합니다. (미수강 = 0)"""
    # 모든 직원과 모든 교육과정이 행렬에 포함되도록 골격 생성
    matrix = ratings_train.pivot(index='emp_id', columns='course_id', values='rating').fillna(0)

    # 누락된 직원이나 과목이 없도록 reindex 수행
    all_emp_ids = employees['emp_id'].unique()
    all_course_ids = courses['course_id'].unique()
    rating_matrix = matrix.reindex(index=all_emp_ids, columns=all_course_ids, fill_value=0)

    return rating_matrix


# ══════════════════════════════════════════════════════════════════════════
# 3. CollaborativeFilter 클래스 (SVD 협업 필터링)
# ══════════════════════════════════════════════════════════════════════════
class CollaborativeFilter:
    def __init__(self, rating_matrix, n_factors=N_FACTORS):
        self.rating_matrix = rating_matrix
        self.user_ids = rating_matrix.index
        self.item_ids = rating_matrix.columns

        # 1) 행 중심화 (Row Centering)
        R = rating_matrix.values
        self.user_ratings_mean = np.mean(R, axis=1)
        R_demeaned = R - self.user_ratings_mean.reshape(-1, 1)

        # 2) SVD 행렬 분해
        # 데이터가 작아 n_factors가 전체 차원보다 클 경우 조정
        k = min(n_factors, min(R.shape) - 1)
        U, sigma, Vt = svds(R_demeaned, k=k)
        sigma = np.diag(sigma)

        # 3) 예측 평점 행렬 복원
        all_user_predicted_ratings = np.dot(np.dot(U, sigma), Vt) + self.user_ratings_mean.reshape(-1, 1)
        self.preds_matrix = pd.DataFrame(all_user_predicted_ratings, index=self.user_ids, columns=self.item_ids)

    def get_scores(self, emp_id):
        """특정 직원의 모든 과목에 대한 예측 점수 Series 반환"""
        if emp_id not in self.preds_matrix.index:
            return pd.Series(0, index=self.item_ids)
        return self.preds_matrix.loc[emp_id]

    def recommend(self, emp_id, top_n=TOP_N, exclude_rated=True):
        scores = self.get_scores(emp_id).copy()

        if exclude_rated and emp_id in self.rating_matrix.index:
            # 수강 이력이 있는 과목 마스킹 (-inf)
            rated_items = self.rating_matrix.loc[emp_id] > 0
            scores[rated_items] = -np.inf

        return scores.sort_values(ascending=False).head(top_n)


# ══════════════════════════════════════════════════════════════════════════
# 4. ContentFilter 클래스 (코사인 유사도 기반 콘텐츠 필터링)
# ══════════════════════════════════════════════════════════════════════════
class ContentFilter:
    def __init__(self, employees, courses, ratings_train, rating_matrix):
        self.rating_matrix = rating_matrix
        self.item_ids = courses['course_id'].values

        # 1) 교육과정 벡터 생성 (category 원핫인코딩 + level)
        cat_dummies = pd.get_dummies(courses['category'], prefix='cat')
        self.course_features = pd.concat([courses[['course_id', 'level']], cat_dummies], axis=1).set_index('course_id')

        # 직원의 역량 지표와 차원을 맞추기 위해 0으로 채워진 컬럼 추가
        for col in ['tenure', 'ai_literacy', 'data_skill', 'leadership']:
            self.course_features[col] = 0.0

        # 2) 직원 프로필 벡터 생성
        emp_features = employees[
            ['emp_id', 'grade_num', 'tenure', 'ai_literacy', 'data_skill', 'leadership']].set_index('emp_id')
        emp_features.rename(columns={'grade_num': 'level'}, inplace=True)  # level 차원 통합

        # 직원의 카테고리 선호도 계산 (기수강 과목의 카테고리 벡터 평균)
        emp_cat_pref = pd.DataFrame(0.0, index=emp_features.index, columns=cat_dummies.columns)
        for emp_id in emp_features.index:
            rated_courses = ratings_train[ratings_train['emp_id'] == emp_id]['course_id']
            if not rated_courses.empty:
                emp_cat_pref.loc[emp_id] = self.course_features.loc[rated_courses, cat_dummies.columns].mean()

        self.emp_features = pd.concat([emp_features, emp_cat_pref], axis=1)

        # 3) 차원 정렬 및 스케일링
        self.course_features = self.course_features[self.emp_features.columns]

        scaler = MinMaxScaler()
        self.emp_features_scaled = scaler.fit_transform(self.emp_features)
        self.course_features_scaled = scaler.fit_transform(self.course_features)

    def get_scores(self, emp_id):
        """직원 벡터와 모든 교육과정 벡터 간의 코사인 유사도 점수 반환"""
        if emp_id not in self.emp_features.index:
            return pd.Series(0, index=self.item_ids)

        emp_idx = self.emp_features.index.get_loc(emp_id)
        emp_vec = self.emp_features_scaled[emp_idx].reshape(1, -1)

        sim_scores = cosine_similarity(emp_vec, self.course_features_scaled).flatten()
        return pd.Series(sim_scores, index=self.course_features.index)

    def recommend(self, emp_id, top_n=TOP_N, exclude_rated=True):
        scores = self.get_scores(emp_id).copy()

        if exclude_rated and emp_id in self.rating_matrix.index:
            rated_items = self.rating_matrix.loc[emp_id] > 0
            scores[rated_items] = -np.inf

        return scores.sort_values(ascending=False).head(top_n)


# ══════════════════════════════════════════════════════════════════════════
# 5. HybridRecommender 클래스
# ══════════════════════════════════════════════════════════════════════════
class HybridRecommender:
    def __init__(self, cf_model, cb_model, rating_matrix):
        self.cf = cf_model
        self.cb = cb_model
        self.rating_matrix = rating_matrix

    def get_scores_and_alpha(self, emp_id):
        cf_raw = self.cf.get_scores(emp_id)
        cb_raw = self.cb.get_scores(emp_id)

        # [조건 4-1] 독립적인 MinMax Scaling (반드시 스케일링 후 가중합)
        scaler = MinMaxScaler()
        cf_scaled = pd.Series(scaler.fit_transform(cf_raw.values.reshape(-1, 1)).flatten(), index=cf_raw.index)
        cb_scaled = pd.Series(scaler.fit_transform(cb_raw.values.reshape(-1, 1)).flatten(), index=cb_raw.index)

        # [조건 4-2] 동적 가중치 (Dynamic Alpha) 적용
        num_rated = (self.rating_matrix.loc[emp_id] > 0).sum() if emp_id in self.rating_matrix.index else 0

        if num_rated <= 2:
            effective_alpha = 0.2  # 수강 이력이 부족하면 Content-Based(프로필) 비중 80%로 확대
        else:
            effective_alpha = ALPHA

        hybrid_scores = (effective_alpha * cf_scaled) + ((1 - effective_alpha) * cb_scaled)

        return hybrid_scores, effective_alpha

    def recommend(self, emp_id, top_n=TOP_N, exclude_rated=True):
        scores, effective_alpha = self.get_scores_and_alpha(emp_id)

        # [조건 4-3] 점수 풀(Pool)에서 사전에 미수강 과목 필터링(Pre-filtering)
        if exclude_rated and emp_id in self.rating_matrix.index:
            rated_items = self.rating_matrix.loc[emp_id] > 0
            scores[rated_items] = -np.inf

        top_scores = scores.sort_values(ascending=False).head(top_n)
        return top_scores, effective_alpha


# ══════════════════════════════════════════════════════════════════════════
# 6. 평가 함수 모듈 (Evaluation)
# ══════════════════════════════════════════════════════════════════════════
def rmse_score(cf_model, ratings_test):
    """CF 모델의 예측 정확도(RMSE) 계산"""
    actuals, preds = [], []
    for _, row in ratings_test.iterrows():
        emp_id, course_id, true_rating = row['emp_id'], row['course_id'], row['rating']
        if emp_id in cf_model.preds_matrix.index and course_id in cf_model.preds_matrix.columns:
            actuals.append(true_rating)
            preds.append(cf_model.preds_matrix.loc[emp_id, course_id])

    if not actuals: return 0.0
    return np.sqrt(mean_squared_error(actuals, preds))


def evaluate(recommender_func, ratings_test, top_k=TOP_N):
    """Precision@K 및 Recall@K 계산"""
    test_users = ratings_test['emp_id'].unique()
    hit_count = 0
    total_recommended = 0
    total_actual = 0

    for emp_id in test_users:
        # 실제 수강 내역 (평점 3 이상을 유의미한 수강으로 간주)
        actual_items = ratings_test[(ratings_test['emp_id'] == emp_id) & (ratings_test['rating'] >= 3)][
            'course_id'].tolist()
        if not actual_items: continue

        # 추천 항목 도출
        recs = recommender_func(emp_id, top_n=top_k, exclude_rated=True)
        if isinstance(recs, tuple): recs = recs[0]  # 하이브리드 리턴값 처리
        recommended_items = recs.index.tolist()

        hits = len(set(recommended_items) & set(actual_items))
        hit_count += hits
        total_recommended += len(recommended_items)
        total_actual += len(actual_items)

    precision = hit_count / total_recommended if total_recommended > 0 else 0
    recall = hit_count / total_actual if total_actual > 0 else 0
    return precision, recall


# ══════════════════════════════════════════════════════════════════════════
# 7. 메인 실행 함수
# ══════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("🎓 사내 맞춤형 교육과정 추천 시스템 가동")
    print("=" * 60)

    try:
        # 1. 데이터 로드 및 전처리
        data = load_excel(EXCEL_PATH)
        courses, employees = data['courses'], data['employees']
        ratings_train, ratings_test, targets = data['ratings_train'], data['ratings_test'], data['recommend_target']

        # 과정명 매핑 딕셔너리
        course_dict = dict(zip(courses['course_id'], courses['name']))

        # Rating 행렬 생성
        rating_matrix = build_rating_matrix(ratings_train, employees, courses)

        # 2. 추천 모델 초기화
        print("\n⚙️ 머신러닝 모델 학습 중...")
        cf = CollaborativeFilter(rating_matrix, n_factors=N_FACTORS)
        cb = ContentFilter(employees, courses, ratings_train, rating_matrix)
        hybrid = HybridRecommender(cf, cb, rating_matrix)

        # 3. 모델 성능 평가
        cf_p, cf_r = evaluate(cf.recommend, ratings_test)
        cb_p, cb_r = evaluate(cb.recommend, ratings_test)
        hb_p, hb_r = evaluate(hybrid.recommend, ratings_test)

        print("\n📊 [모델 평가 결과]")
        print(f" - CF 예측 RMSE: {rmse_score(cf, ratings_test):.4f}")
        print(f" - CF 모델      | Precision@{TOP_N}: {cf_p:.3f} | Recall@{TOP_N}: {cf_r:.3f}")
        print(f" - CB 모델      | Precision@{TOP_N}: {cb_p:.3f} | Recall@{TOP_N}: {cb_r:.3f}")
        print(f" - 하이브리드   | Precision@{TOP_N}: {hb_p:.3f} | Recall@{TOP_N}: {hb_r:.3f}")

        # 4. 대상자 추천 생성 및 콘솔 출력
        print("\n\n" + "=" * 60)
        print("🎯 [추천 대상 직원별 Top-N 추천 결과]")
        print("=" * 60)

        export_data = []  # 엑셀 저장을 위한 리스트

        for _, row in targets.iterrows():
            emp_id, dept, grade = row['emp_id'], row['dept'], row['grade']
            tenure = int(row['tenure'])
            num_rated = (rating_matrix.loc[emp_id] > 0).sum() if emp_id in rating_matrix.index else 0

            print(f"\n[{emp_id}] {dept} | {grade} | 근속 {tenure}년 | 기수강 {num_rated}건")

            # ① 협업 필터링 (CF)
            print("\n  ① 협업 필터링")
            cf_recs = cf.recommend(emp_id, TOP_N, exclude_rated=True)
            for i, (c_id, score) in enumerate(cf_recs.items(), 1):
                print(f"    {i}. [{c_id}] {course_dict.get(c_id, '')[:15]:<15}\t{score:.3f}")

            # ② 콘텐츠 필터링 (CB)
            print("\n  ② 콘텐츠 필터링")
            cb_recs = cb.recommend(emp_id, TOP_N, exclude_rated=True)
            for i, (c_id, score) in enumerate(cb_recs.items(), 1):
                print(f"    {i}. [{c_id}] {course_dict.get(c_id, '')[:15]:<15}\t{score:.3f}")

            # ③ 하이브리드 (Hybrid)
            print("\n  ③ 하이브리드")
            hb_recs, alpha = hybrid.recommend(emp_id, TOP_N, exclude_rated=True)
            for i, (c_id, score) in enumerate(hb_recs.items(), 1):
                print(
                    f"    {i}. [{c_id}] {course_dict.get(c_id, '')[:15]:<15}\t{score:.3f}  CF:{alpha:.2f} / CB:{1 - alpha:.2f}")

                # 엑셀 저장용 데이터 수집 (하이브리드 Top-3)
                if i <= 3:
                    export_data.append({
                        'emp_id': emp_id,
                        'dept': dept,
                        'grade': grade,
                        'rank': i,
                        'course_id': c_id,
                        'course_name': course_dict.get(c_id, ''),
                        'hybrid_score': round(score, 3)
                    })

        # 5. 결과를 엑셀로 저장
        save_dir = os.path.dirname(EXCEL_PATH)
        output_file = os.path.join(save_dir, 'recommendations.xlsx')

        pd.DataFrame(export_data).to_excel(output_file, index=False)
        print("\n" + "=" * 60)
        print(f"💾 하이브리드 Top-3 추천 결과가 엑셀로 저장되었습니다.\n경로: {output_file}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ [시스템 오류] 처리 중 문제가 발생했습니다: {e}")


if __name__ == "__main__":
    main()