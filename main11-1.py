import pandas as pd
import os
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. 파일 경로 및 데이터 로드
# ==========================================
file_path = r"C:\Users\b2209\OneDrive\바탕 화면\박효근\20202855 박효근\26년도 1학기\AI기반피플애널리틱스\project#11\11_PAproject_11_1_recruit.xlsx"
output_path = os.path.join(os.path.dirname(file_path), "dashboard.html")

print("데이터를 불러오는 중입니다...")
df_ts = pd.read_excel(file_path, sheet_name='timeseries')
df_detail = pd.read_excel(file_path, sheet_name='detail')
df_skills = pd.read_excel(file_path, sheet_name='skills')

# ==========================================
# 2. 데이터 전처리 (자바스크립트 로직에 맞게 ym 규격화)
# ==========================================
# 자바스크립트 코드에서 ym.split('-') 등을 사용하므로,
# 파이썬에서 year와 month를 조합하여 'YYYY-MM' 형태의 문자열로 완벽하게 통일해 줍니다.
df_ts['ym'] = df_ts['year'].astype(str) + '-' + df_ts['month'].astype(str).str.zfill(2)
df_detail['ym'] = df_detail['year'].astype(str) + '-' + df_detail['month'].astype(str).str.zfill(2)
df_skills['ym'] = df_skills['year'].astype(str) + '-' + df_skills['month'].astype(str).str.zfill(2)

# ==========================================
# 3. 데이터를 JSON 문자열로 변환
# ==========================================
# 자바스크립트 변수(tsData 등)에 배열 형태로 바로 주입하기 위해 orient='records' 사용
ts_json = df_ts.to_json(orient='records', force_ascii=False)
dt_json = df_detail.to_json(orient='records', force_ascii=False)
sk_json = df_skills.to_json(orient='records', force_ascii=False)

# ==========================================
# 4. HTML 템플릿 결합 및 파일 저장
# ==========================================
print("제공해주신 템플릿에 데이터를 주입하여 HTML을 생성 중입니다...")

# 사용자가 제공한 템플릿 (f-string을 통해 ts_json, dt_json, sk_json 변수가 자동으로 주입됨)
html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>채용 데이터 분석 대시보드</title>
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
    <style>
        *, *::before, *::after {{
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Malgun Gothic', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f6f9;
            margin: 0;
            padding: 0;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #1f4068, #162447);
            color: white;
            padding: 24px 40px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0;
            font-size: 26px;
            font-weight: 600;
        }}
        .header p {{
            margin: 5px 0 0 0;
            font-size: 14px;
            color: #cbd5e1;
        }}
        .container {{
            max-width: 1440px;
            margin: 30px auto;
            padding: 0 20px;
        }}
        /* 탭 네비게이션 스타일 */
        .tabs {{
            display: flex;
            border-bottom: 2px solid #e2e8f0;
            margin-bottom: 25px;
            gap: 5px;
        }}
        .tab {{
            padding: 12px 24px;
            cursor: pointer;
            background: #e2e8f0;
            border: none;
            border-radius: 6px 6px 0 0;
            font-size: 15px;
            font-weight: 600;
            color: #4a5568;
            transition: all 0.2s ease;
        }}
        .tab:hover {{
            background: #cbd5e1;
            color: #1a202c;
        }}
        .tab.active {{
            background: #fff;
            color: #1f4068;
            border-bottom: 3px solid #1f4068;
            margin-bottom: -2px;
            box-shadow: 0 -2px 4px rgba(0,0,0,0.05);
        }}
        /* 탭 콘텐츠 스타일 */
        .tab-content {{
            display: none;
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}
        .tab-content.active {{
            display: block;
        }}
        /* 필터 선택 상자 */
        .filter-container {{
            background: #f8fafc;
            padding: 15px 20px;
            border-radius: 6px;
            margin-bottom: 20px;
            border: 1px solid #e2e8f0;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .filter-container label {{
            font-weight: 600;
            color: #334155;
        }}
        .filter-container select {{
            padding: 8px 16px;
            border-radius: 4px;
            border: 1px solid #cbd5e1;
            background-color: white;
            font-size: 14px;
            min-width: 220px;
            outline: none;
        }}
        .filter-container select:focus {{
            border-color: #1f4068;
        }}
        /* 레이아웃 구조 */
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
        }}
        .chart-box {{
            background: #fff;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 15px;
            min-height: 480px;
        }}
        .full-width {{
            grid-column: span 2;
        }}
        /* 요약 카드 */
        .metrics-row {{
            display: flex;
            gap: 20px;
            margin-bottom: 25px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            border-left: 5px solid #1f4068;
            min-width: 250px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }}
        .metric-title {{
            font-size: 13px;
            color: #64748b;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: 700;
            color: #1e293b;
        }}
    </style>
</head>
<body>

    <div class="header">
        <h1>채용 데이터 분석 대시보드</h1>
        <p>인사운영 및 직종·산업별·스킬셋 채용 트렌드 분석 리포트</p>
    </div>

    <div class="container">
        <div class="tabs">
            <button class="tab active" onclick="switchTab('tab1')">1. 전체 추이</button>
            <button class="tab" onclick="switchTab('tab2')">2. 직종별 분석</button>
            <button class="tab" onclick="switchTab('tab3')">3. 산업별 분석</button>
            <button class="tab" onclick="switchTab('tab4')">4. 스킬 트렌드</button>
        </div>

        <div id="tab1" class="tab-content active">
            <div class="metrics-row" id="summary-metrics"></div>
            <div class="grid-2">
                <div class="chart-box full-width" id="chart-ts-main"></div>
                <div class="chart-box full-width" id="chart-ts-yoy"></div>
            </div>
        </div>

        <div id="tab2" class="tab-content">
            <div class="filter-container">
                <label for="job-selector">분석 직종 선택:</label>
                <select id="job-selector" onchange="updateJobCharts()"></select>
            </div>
            <div class="grid-2">
                <div class="chart-box" id="chart-job-line"></div>
                <div class="chart-box" id="chart-job-heatmap"></div>
            </div>
        </div>

        <div id="tab3" class="tab-content">
            <div class="grid-2">
                <div class="chart-box" id="chart-ind-pie"></div>
                <div class="chart-box" id="chart-ind-heatmap"></div>
            </div>
        </div>

        <div id="tab4" class="tab-content">
            <div class="filter-container">
                <label for="skill-selector">스킬 키워드 선택:</label>
                <select id="skill-selector" onchange="updateSkillCharts()"></select>
            </div>
            <div class="grid-2">
                <div class="chart-box full-width" id="chart-skill-line"></div>
            </div>
        </div>
    </div>

    <script>
        // 파이썬으로부터 주입받은 원본 데이터
        const tsData = {ts_json};
        const detailData = {dt_json};
        const skillData = {sk_json};

        // 탭 전환 함수
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));

            document.getElementById(tabId).classList.add('active');
            event.currentTarget.classList.add('active');

            // 탭 이동 시 차트 깨짐 방지용 리사이즈 크리거
            window.dispatchEvent(new Event('resize'));
        }}

        // 초기 대시보드 렌더링
        window.onload = function() {{
            initTab1();
            initTab2();
            initTab3();
            initTab4();
        }};

        // ==========================================
        // 1. 전체 추이 탭
        // ==========================================
        function initTab1() {{
            // ym 별 전체 공고수 집계
            const ymMap = {{}};
            tsData.forEach(d => {{
                if(!ymMap[d.ym]) ymMap[d.ym] = 0;
                ymMap[d.ym] += d.posting_count;
            }});

            const sortedYMs = Object.keys(ymMap).sort();
            const counts = sortedYMs.map(ym => ymMap[ym]);

            // YoY 증감률 계산 (전년 동월 비교)
            const yoyValues = sortedYMs.map((ym) => {{
                const currentVal = ymMap[ym];
                const parts = ym.split('-');
                const prevYear = parseInt(parts[0]) - 1;
                const prevYM = prevYear + '-' + parts[1];
                if(ymMap[prevYM]) {{
                    const prevVal = ymMap[prevYM];
                    return ((currentVal - prevVal) / prevVal * 100).toFixed(1);
                }}
                return null;
            }});

            // 요약 상단 카드
            const totalSum = counts.reduce((a,b)=>a+b, 0);
            const latestYM = sortedYMs[sortedYMs.length - 1] || '-';
            const latestCount = ymMap[latestYM] || 0;

            document.getElementById('summary-metrics').innerHTML = `
                <div class="metric-card">
                    <div class="metric-title">수집기간 누적 전체 공고 수</div>
                    <div class="metric-value">${{totalSum.toLocaleString()}} 건</div>
                </div>
                <div class="metric-card" style="border-left-color: #38bdf8;">
                    <div class="metric-title">최근 월 공고 수 (${{latestYM}})</div>
                    <div class="metric-value">${{latestCount.toLocaleString()}} 건</div>
                </div>
            `;

            // 월별 전체 공고 수 라인차트
            const traceMain = {{
                x: sortedYMs,
                y: counts,
                type: 'scatter',
                mode: 'lines+markers',
                name: '공고 수',
                line: {{ color: '#1f4068', width: 3 }},
                marker: {{ size: 6 }}
            }};
            Plotly.newPlot('chart-ts-main', [traceMain], {{
                title: '<b>월별 전체 채용 공고 수 추이</b>',
                xaxis: {{ title: '연월(YM)' }},
                yaxis: {{ title: '공고 수 (건)' }}
            }});

            // YoY 증감률 바차트
            const validYoYIndex = yoyValues.map((v, i) => v !== null ? i : -1).filter(i => i !== -1);
            const traceYoY = {{
                x: validYoYIndex.map(i => sortedYMs[i]),
                y: validYoYIndex.map(i => parseFloat(yoyValues[i])),
                type: 'bar',
                name: 'YoY 증감률 (%)',
                marker: {{
                    color: validYoYIndex.map(i => parseFloat(yoyValues[i]) >= 0 ? '#10b981' : '#ef4444')
                }}
            }};
            Plotly.newPlot('chart-ts-yoy', [traceYoY], {{
                title: '<b>전년 동월 대비(YoY) 공고 수 증감률</b>',
                xaxis: {{ title: '연월(YM)' }},
                yaxis: {{ title: '증감률 (%)', ticksuffix: '%' }}
            }});
        }}

        // ==========================================
        // 2. 직종별 분석 탭
        // ==========================================
        function initTab2() {{
            const jobs = [...new Set(tsData.map(d => d.job_category))].sort();
            const selector = document.getElementById('job-selector');
            jobs.forEach(j => {{
                const opt = document.createElement('option');
                opt.value = j; opt.innerText = j;
                selector.appendChild(opt);
            }});
            updateJobCharts();
        }}

        function updateJobCharts() {{
            const selectedJob = document.getElementById('job-selector').value;
            const jobFiltered = tsData.filter(d => d.job_category === selectedJob);

            // 월별 추이 라인 차트
            const traceLine = {{
                x: jobFiltered.map(d => d.ym),
                y: jobFiltered.map(d => d.posting_count),
                type: 'scatter',
                mode: 'lines+markers',
                line: {{ color: '#e43f5a', width: 3 }}
            }};
            Plotly.newPlot('chart-job-line', [traceLine], {{
                title: `<b>${{selectedJob}} - 월별 공고수 추이</b>`,
                xaxis: {{ title: '연월(YM)' }},
                yaxis: {{ title: '공고 수 (건)' }}
            }});

            // 직종별 전체 월별 분포 히트맵 
            const allJobs = [...new Set(tsData.map(d => d.job_category))].sort();
            const allYMs = [...new Set(tsData.map(d => d.ym))].sort();

            const zData = allJobs.map(j => {{
                return allYMs.map(ym => {{
                    const match = tsData.find(d => d.job_category === j && d.ym === ym);
                    return match ? match.posting_count : 0;
                }});
            }});

            const traceHeatmap = {{
                x: allYMs, y: allJobs, z: zData,
                type: 'heatmap', colorscale: 'Blues'
            }};
            Plotly.newPlot('chart-job-heatmap', [traceHeatmap], {{
                title: '<b>전체 직종 × 연월 채용공고 히트맵</b>',
                xaxis: {{ title: '연월(YM)' }},
                yaxis: {{ automargin: true }}
            }});
        }}

        // ==========================================
        // 3. 산업별 분석 탭
        // ==========================================
        function initTab3() {{
            // 산업별 누적 비중 계산
            const indMap = {{}};
            detailData.forEach(d => {{
                if(!indMap[d.industry]) indMap[d.industry] = 0;
                indMap[d.industry] += d.posting_count;
            }});

            // 도넛 차트
            const tracePie = {{
                labels: Object.keys(indMap),
                values: Object.values(indMap),
                type: 'pie', hole: 0.4,
                textinfo: 'percent+label'
            }};
            Plotly.newPlot('chart-ind-pie', [tracePie], {{
                title: '<b>산업별 채용 공고 비중 (도넛 차트)</b>',
                showlegend: true
            }});

            // 직종 x 산업 교차 히트맵
            const allJobs = [...new Set(detailData.map(d => d.job_category))].sort();
            const allIndustries = [...new Set(detailData.map(d => d.industry))].sort();

            const zCross = allJobs.map(j => {{
                return allIndustries.map(ind => {{
                    return detailData
                        .filter(d => d.job_category === j && d.industry === ind)
                        .reduce((sum, curr) => sum + curr.posting_count, 0);
                }});
            }});

            const traceCross = {{
                x: allIndustries, y: allJobs, z: zCross,
                type: 'heatmap', colorscale: 'YlGnBu'
            }};
            Plotly.newPlot('chart-ind-heatmap', [traceCross], {{
                title: '<b>직종 × 산업군 교차 채용 분포</b>',
                xaxis: {{ title: '산업군' }},
                yaxis: {{ automargin: true }}
            }});
        }}

        // ==========================================
        // 4. 스킬 트렌드 탭
        // ==========================================
        function initTab4() {{
            const skills = [...new Set(skillData.map(d => d.skill_keyword))].sort();
            const selector = document.getElementById('skill-selector');
            skills.forEach(s => {{
                const opt = document.createElement('option');
                opt.value = s; opt.innerText = s;
                selector.appendChild(opt);
            }});
            updateSkillCharts();
        }}

        function updateSkillCharts() {{
            const selectedSkill = document.getElementById('skill-selector').value;
            const skillFiltered = skillData.filter(d => d.skill_keyword === selectedSkill);
            skillFiltered.sort((a,b) => a.ym.localeCompare(b.ym));

            // 최초 월과 최신 월의 빈도를 비교하여 급등 / 감소 / 유지 상태 구분 규칙 지정
            let statusText = "안정/유지";
            let statusColor = "#64748b";

            if(skillFiltered.length >= 2) {{
                const startVal = skillFiltered[0].frequency_per_1000;
                const endVal = skillFiltered[skillFiltered.length - 1].frequency_per_1000;
                const changePct = ((endVal - startVal) / startVal * 100);

                if(changePct >= 15) {{
                    statusText = `급등 트렌드 (+${{changePct.toFixed(1)}}%)`;
                    statusColor = '#ef4444'; // Red
                }} else if(changePct <= -15) {{
                    statusText = `감소 트렌드 (${{changePct.toFixed(1)}}%)`;
                    statusColor = '#3b82f6'; // Blue
                }} else {{
                    statusText = `유지/보합 (${{changePct >= 0 ? '+' : ''}}${{changePct.toFixed(1)}}%)`;
                }}
            }}

            const traceSkill = {{
                x: skillFiltered.map(d => d.ym),
                y: skillFiltered.map(d => d.frequency_per_1000),
                type: 'scatter', mode: 'lines+markers',
                line: {{ color: statusColor, width: 3 }},
                marker: {{ size: 6 }}
            }};

            Plotly.newPlot('chart-skill-line', [traceSkill], {{
                title: `<b>${{selectedSkill}} 빈도 트렌드 (상태: <span style="color:${{statusColor}}">${{statusText}}</span>)</b>`,
                xaxis: {{ title: '연월(YM)' }},
                yaxis: {{ title: '1,000건당 노출 빈도 (회)' }}
            }});
        }}
    </script>
</body>
</html>
"""

# HTML 파일 저장 (인코딩 utf-8-sig 지정하여 한글 깨짐 방지)
with open(output_path, "w", encoding="utf-8-sig") as f:
    f.write(html_content)

print("\n" + "=" * 60)
print(f"✅ 클라이언트 사이드 렌더링 기반 대시보드 생성이 완료되었습니다.")
print(f"📁 저장 경로: {output_path}")
print("=" * 60)