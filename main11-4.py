import os
import json
import pandas as pd


def analyze_skills_trend(file_path, output_html="skills_trend.html"):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"엑셀 파일을 찾을 수 없습니다: {file_path}")

    print("스킬 데이터를 로드하고 분석 중입니다...")
    df_sk = pd.read_excel(file_path, sheet_name='skills')

    # ----------------------------------------------------
    # 데이터 통계 및 전처리 (Python에서 사전 연산 수행)
    # ----------------------------------------------------

    # 분석 1용: 월별 원본 데이터 정렬 및 JSON 변환
    df_sk = df_sk.sort_values(by=['ym', 'skill_keyword'])
    ts_json = df_sk.to_json(orient='records', force_ascii=False)

    # 연도별 평균 빈도 데이터 세팅 (바차트, 히트맵용)
    df_yr = df_sk.groupby(['year', 'skill_keyword'])['frequency_per_1000'].mean().reset_index()

    # 피벗 테이블 생성 (행: 키워드, 열: 연도)
    df_pivot = df_yr.pivot(index='skill_keyword', columns='year', values='frequency_per_1000').fillna(0)
    available_years = [int(c) for c in df_pivot.columns]

    # 2020년 및 2024년 존재 여부 확인 (없을 경우 최소/최대 연도로 대체)
    y_start = 2020 if 2020 in available_years else min(available_years)
    y_end = 2024 if 2024 in available_years else max(available_years)

    # 분석 2용: 시작연도 vs 종료연도 Top 10 데이터 추출
    top_start = df_pivot[y_start].nlargest(10).reset_index().to_dict(orient='records')
    top_end = df_pivot[y_end].nlargest(10).reset_index().to_dict(orient='records')

    # 분석 3용: 급등 vs 감소 키워드 연산 (시작연도 평균 빈도가 5 이상인 스킬 대상)
    df_shift = df_pivot[[y_start, y_end]].copy()
    df_shift = df_shift[df_shift[y_start] >= 5]  # 소수점 노이즈 제거
    df_shift['change_rate'] = ((df_shift[y_end] - df_shift[y_start]) / df_shift[y_start]) * 100

    top_rising = df_shift['change_rate'].nlargest(5).reset_index().to_dict(orient='records')
    top_falling = df_shift['change_rate'].nsmallest(5).reset_index().to_dict(orient='records')

    # 분석 4용: 히트맵 데이터 구조화
    heatmap_data = {
        'y': df_pivot.index.tolist(),
        'x': [str(yr) for yr in df_pivot.columns],
        'z': df_pivot.values.tolist()
    }

    # 분석 5용: 신규 등장(라이징) 키워드 강조 필터링
    cols_pre = [c for c in df_pivot.columns if c <= 2021]
    cols_post = [c for c in df_pivot.columns if c >= 2023]

    new_skills = []
    if cols_pre and cols_post:
        df_pivot['pre_mean'] = df_pivot[cols_pre].mean(axis=1)
        df_pivot['post_mean'] = df_pivot[cols_post].mean(axis=1)

        # 2021년 이전 10 이하, 2023년 이후 급증(예: 15 초과) 조건
        df_new = df_pivot[(df_pivot['pre_mean'] <= 10) & (df_pivot['post_mean'] > 15)]
        df_new = df_new.sort_values(by='post_mean', ascending=False)
        new_skills = df_new.reset_index()[['skill_keyword', 'pre_mean', 'post_mean']].to_dict(orient='records')

    # ----------------------------------------------------
    # HTML & JavaScript 통합 대시보드 템플릿 주입
    # ----------------------------------------------------
    print("대시보드 HTML을 렌더링 중입니다...")

    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>HR 노동시장 역량 스킬 트렌드 분석</title>
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
    <style>
        body {{
            font-family: 'Malgun Gothic', sans-serif;
            background-color: #f8fafc;
            margin: 0; padding: 20px;
            color: #1e293b;
        }}
        .header {{
            background: linear-gradient(135deg, #0f172a, #1e293b);
            color: white; padding: 25px;
            border-radius: 10px; margin-bottom: 25px;
        }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .header p {{ margin: 5px 0 0 0; color: #94a3b8; font-size: 14px; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 25px;
        }}
        .card {{
            background: white; border: 1px solid #e2e8f0;
            border-radius: 8px; padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }}
        .full {{ grid-column: span 2; }}
        .filter-box {{
            background: #f1f5f9; padding: 15px;
            border-radius: 6px; margin-bottom: 15px;
            display: flex; flex-direction: column; gap: 8px;
        }}
        select[multiple] {{
            width: 100%; height: 100px; padding: 8px;
            border-radius: 4px; border: 1px solid #cbd5e1;
        }}
        .new-badge-table {{
            width: 100%; border-collapse: collapse; margin-top: 10px;
        }}
        .new-badge-table th, .new-badge-table td {{
            padding: 10px; border: 1px solid #e2e8f0; text-align: left;
        }}
        .new-badge-table th {{ background: #f1f5f9; }}
        .badge {{
            background: #ef4444; color: white; padding: 2px 6px;
            border-radius: 4px; font-size: 11px; font-weight: bold;
        }}
    </style>
</head>
<body>

    <div class="header">
        <h1>💡 노동시장 요구 역량(스킬셋) 시계열 트렌드 대시보드</h1>
        <p>채용공고 내 키워드 등장 빈도 추적 분석 ({y_start}년 ➔ {y_end}년)</p>
    </div>

    <div class="grid">
        <div class="card full">
            <h3>1. 스킬셋별 월별 등장 빈도 추이 추적</h3>
            <div class="filter-box">
                <label for="skill-dropdown"><b>스킬 키워드 선택 (Ctrl/Cmd를 누르고 클릭하여 복수 선택 가능):</b></label>
                <select id="skill-dropdown" multiple onchange="updateLineChart()"></select>
            </div>
            <div id="chart-line" style="height: 400px;"></div>
        </div>

        <div class="card">
            <h3>2. {y_start}년 vs {y_end}년 수요 Top 10 역량 비교</h3>
            <div id="chart-bar-comp" style="height: 450px;"></div>
        </div>

        <div class="card">
            <h3>3. 시장 수요 급상승 vs 급감 역량 (상위 5개)</h3>
            <div id="chart-bar-shift" style="height: 450px;"></div>
        </div>

        <div class="card full">
            <h3>4. 전체 역량 키워드 × 연도별 수요 매트릭스 히트맵</h3>
            <div id="chart-heatmap" style="height: 600px;"></div>
        </div>

        <div class="card full">
            <h3>🚀 5. 시장 대세 신규 등장(라이징) 역량 특화 강조</h3>
            <p style="font-size: 13px; color:#64748b; margin-top:-10px;">
                * 판별 조건: 2021년 이전까지는 평균 빈도가 10 이하로 주류가 아니었다가, 2023년 이후 평균 빈도가 크게 증가한 기술 스킬셋
            </p>
            <table class="new-badge-table">
                <thead>
                    <tr>
                        <th>스킬 키워드</th>
                        <th>~2021년 평균 빈도 (1,000건당)</th>
                        <th>2023년~ 현재 평균 빈도 (1,000건당)</th>
                        <th>상태</th>
                    </tr>
                </thead>
                <tbody id="new-skills-body"></tbody>
            </table>
        </div>
    </div>

    <script>
        // 파이썬 연산 데이터 수신
        const tsData = {ts_json};
        const topStart = {json.dumps(top_start, ensure_ascii=False)};
        const topEnd = {json.dumps(top_end, ensure_ascii=False)};
        const rising = {json.dumps(top_rising, ensure_ascii=False)};
        const falling = {json.dumps(top_falling, ensure_ascii=False)};
        const hData = {json.dumps(heatmap_data, ensure_ascii=False)};
        const newSkills = {json.dumps(new_skills, ensure_ascii=False)};

        const yStart = "{y_start}";
        const yEnd = "{y_end}";

        // 초기 구동
        initDashboard();

        function initDashboard() {{
            // 1. 드롭다운 목록 채우기
            const allSkills = [...new Set(tsData.map(d => d.skill_keyword))].sort();
            const select = document.getElementById('skill-dropdown');
            allSkills.forEach((sk, idx) => {{
                const opt = document.createElement('option');
                opt.value = sk; opt.innerText = sk;
                if(idx < 3) opt.selected = true; // 초기 상위 3개 자동 선택
                select.appendChild(opt);
            }});

            // 차트들 렌더링
            updateLineChart();
            renderComparisonBar();
            renderShiftBar();
            renderHeatmap();
            renderNewSkillsTable();
        }}

        // 1. 드롭다운 다중 선택 라인차트 업데이트
        function updateLineChart() {{
            const select = document.getElementById('skill-dropdown');
            const selectedOptions = Array.from(select.selectedOptions).map(o => o.value);

            const traces = selectedOptions.map(sk => {{
                const filtered = tsData.filter(d => d.skill_keyword === sk)
                                       .sort((a,b) => a.ym.localeCompare(b.ym));
                return {{
                    x: filtered.map(d => d.ym),
                    y: filtered.map(d => d.frequency_per_1000),
                    type: 'scatter', mode: 'lines+markers', name: sk
                }};
            }});

            Plotly.newPlot('chart-line', traces, {{
                xaxis: {{ title: '연월(YM)' }},
                yaxis: {{ title: '1,000건당 빈도' }},
                margin: {{ t:20, b:40, l:50, r:20 }},
                template: 'plotly_white'
            }});
        }}

        // 2. Top 10 비교 바차트
        function renderComparisonBar() {{
            const trace1 = {{
                x: topStart.map(d => d.frequency_per_1000),
                y: topStart.map(d => d.skill_keyword),
                type: 'bar', orientation: 'h', name: yStart + '년',
                marker: {{ color: '#94a3b8' }}
            }};
            const trace2 = {{
                x: topEnd.map(d => d.frequency_per_1000),
                y: topEnd.map(d => d.skill_keyword),
                type: 'bar', orientation: 'h', name: yEnd + '년',
                marker: {{ color: '#1e293b' }}
            }};

            Plotly.newPlot('chart-bar-comp', [trace1, trace2], {{
                barmode: 'group',
                yaxis: {{ autorange: 'reversed', automargin: true }},
                xaxis: {{ title: '평균 노출 빈도' }},
                margin: {{ t:20, b:40, l:100, r:20 }},
                template: 'plotly_white'
            }});
        }}

        // 3. 급등 vs 감소 키워드 바차트
        function renderShiftBar() {{
            const traceRising = {{
                x: rising.map(d => d.change_rate),
                y: rising.map(d => d.skill_keyword),
                type: 'bar', orientation: 'h', name: '수요 급등 (Rise)',
                marker: {{ color: '#ef4444' }}
            }};
            const traceFalling = {{
                x: falling.map(d => d.change_rate),
                y: falling.map(d => d.skill_keyword),
                type: 'bar', orientation: 'h', name: '수요 감소 (Drop)',
                marker: {{ color: '#3b82f6' }}
            }};

            Plotly.newPlot('chart-bar-shift', [traceRising, traceFalling], {{
                yaxis: {{ automargin: true, autorange: 'reversed' }},
                xaxis: {{ title: '수요 변화율 (%)', ticksuffix: '%' }},
                margin: {{ t:20, b:40, l:100, r:20 }},
                template: 'plotly_white'
            }});
        }}

        // 4. 매트릭스 히트맵
        function renderHeatmap() {{
            const trace = {{
                x: hData.x, y: hData.y, z: hData.z,
                type: 'heatmap', colorscale: 'Viridis'
            }};
            Plotly.newPlot('chart-heatmap', [trace], {{
                xaxis: {{ title: '연도 (Year)', type: 'category' }},
                yaxis: {{ automargin: true }},
                margin: {{ t:20, b:40, l:120, r:20 }}
            }});
        }}

        // 5. 신규 등장 라이징 기술 스킬셋 테이블 표기
        function renderNewSkillsTable() {{
            const tbody = document.getElementById('new-skills-body');
            tbody.innerHTML = "";
            if (newSkills.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:#94a3b8;">조건에 맞는 신규 라이징 키워드가 데이터 내에 존재하지 않습니다.</td></tr>`;
                return;
            }}
            newSkills.forEach(sk => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><b>${{sk.skill_keyword}}</b></td>
                    <td>${{sk.pre_mean.toFixed(1)}} 회</td>
                    <td><span style="color:#ef4444; font-weight:bold;">${{sk.post_mean.toFixed(1)}} 회</span></td>
                    <td><span class="badge">NEW TREND</span></td>
                `;
                tbody.appendChild(tr);
            }});
        }}
    </script>
</body>
</html>
"""

    with open(output_html, 'w', encoding='utf-8-sig') as f:
        f.write(html_content)
    print(f"\n✅ 분석 성공! 결과물이 다음 경로에 저장되었습니다: \n{output_html}")


if __name__ == "__main__":
    EXCEL_PATH = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#11\11_PAproject_11_1_recruit.xlsx"

    # 바탕화면에 바로 html이 생성되도록 경로 지정
    OUTPUT_PATH = os.path.join(os.path.dirname(EXCEL_PATH), "skills_trend.html")

    analyze_skills_trend(EXCEL_PATH, OUTPUT_PATH)