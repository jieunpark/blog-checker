import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import time
import pandas as pd
from datetime import datetime
import math

def format_date(date_str):
    """발행일을 원하는 포맷으로 변경"""
    try:
        # RSS 날짜 파싱
        dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')

        # 요일 매핑
        weekdays = ['월', '화', '수', '목', '금', '토', '일']
        weekday = weekdays[dt.weekday()]

        # 포맷 변경: "2026-01-01 수 16시43분 00초"
        formatted = dt.strftime(f'%Y-%m-%d {weekday} %H시%M분 %S초')
        return formatted
    except:
        return date_str

def get_blog_posts(blog_id, count=100):
    """네이버 블로그 RSS에서 최근 글 가져오기"""
    rss_url = f"https://blog.rss.naver.com/{blog_id}.xml"
    feed = feedparser.parse(rss_url)

    # RSS 피드에서 실제로 받은 글 개수 확인
    total_entries = len(feed.entries)
    print(f"RSS 피드에서 받은 전체 글 개수: {total_entries}")

    posts = []
    for entry in feed.entries[:count]:
        published_date = entry.published if 'published' in entry else ''
        formatted_date = format_date(published_date) if published_date else ''

        posts.append({
            '제목': entry.title,
            'URL': entry.link,
            '발행일': formatted_date
        })
    return posts, total_entries

def check_indexing(blog_id, title):
    """네이버 검색에서 인덱싱 여부 확인 (개선된 버전)"""
    try:
        # 검색 URL 생성
        encoded_title = quote(f'"{title}"')
        search_url = f"https://search.naver.com/search.naver?ssc=tab.blog.all&query={encoded_title}"

        # 검색 실행
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(search_url, headers=headers, timeout=10)

        # BeautifulSoup으로 파싱
        soup = BeautifulSoup(response.text, 'html.parser')

        # 검색 결과 영역에서만 확인
        # div.api_subject_bx: 블로그 검색 결과 항목
        search_results = soup.select('div.api_subject_bx')

        if not search_results:
            # 검색 결과가 없는 경우 (다른 구조일 수도 있으므로 fallback)
            if f"blog.naver.com/{blog_id}" in response.text:
                return "정상 (전체)"
            else:
                return "누락"

        # 검색 결과 영역에서 본인 블로그 URL 찾기
        for result in search_results:
            result_html = str(result)
            if f"blog.naver.com/{blog_id}" in result_html:
                return "정상"

        return "누락"

    except Exception as e:
        return f"오류: {str(e)}"

# CSS 스타일 추가
st.markdown("""
<style>
    .status-normal {
        background-color: #28a745;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        text-align: center;
    }
    .status-missing {
        background-color: #dc3545;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        text-align: center;
    }
    .status-normal-full {
        background-color: #17a2b8;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Streamlit UI
st.title("📊 네이버 블로그 인덱싱 체크 v2 (개선)")
st.write("블로그의 최근 글들이 네이버 검색에 제대로 노출되는지 확인합니다.")
st.info("🔍 개선사항: BeautifulSoup으로 실제 검색 결과 영역에서만 확인합니다.")

# 입력
blog_id = st.text_input("블로그 아이디", value="money-park")
post_count = st.number_input("확인할 글 개수", min_value=1, max_value=50, value=50)

# 실행 버튼
if st.button("🔍 검색 시작", type="primary"):
    with st.spinner("블로그 글 목록을 가져오는 중..."):
        posts, total_entries = get_blog_posts(blog_id, post_count)

    if not posts:
        st.error("블로그 글을 가져올 수 없습니다. 블로그 아이디를 확인해주세요.")
    else:
        if total_entries < post_count:
            st.warning(f"⚠️ RSS 피드에서 {total_entries}개만 제공됩니다. (요청: {post_count}개)")
        st.success(f"총 {len(posts)}개 글을 찾았습니다.")

        # 프로그레스 바
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 결과 저장
        results = []

        for idx, post in enumerate(posts):
            status_text.text(f"확인 중: {idx+1}/{len(posts)} - {post['제목'][:30]}...")

            # 인덱싱 체크
            status = check_indexing(blog_id, post['제목'])

            results.append({
                '번호': idx + 1,
                '제목': post['제목'],
                '발행일': post['발행일'],
                '누락 여부': status,
                'URL': post['URL']
            })

            # 프로그레스 업데이트
            progress_bar.progress((idx + 1) / len(posts))

            # 요청 간격 (네이버 차단 방지)
            time.sleep(0.5)

        status_text.text("✅ 완료!")

        # 결과 저장 (session state에 저장하여 페이지 변경 시에도 유지)
        st.session_state['results'] = results
        st.session_state['blog_id'] = blog_id

# 결과가 있을 때만 표시
if 'results' in st.session_state and st.session_state['results']:
    results = st.session_state['results']
    blog_id = st.session_state['blog_id']

    # 결과 표시
    df = pd.DataFrame(results)

    # 통계
    st.subheader("📈 요약")
    col1, col2, col3 = st.columns(3)
    total = len(df)
    normal = len(df[df['누락 여부'] == '정상'])
    missing = len(df[df['누락 여부'] == '누락'])

    col1.metric("전체 글", total)
    col2.metric("정상", normal, delta=f"{normal/total*100:.1f}%")
    col3.metric("누락", missing, delta=f"-{missing/total*100:.1f}%" if missing > 0 else "0%")

    # 페이징 설정
    st.subheader("📋 상세 결과")
    items_per_page = 50
    total_pages = math.ceil(len(df) / items_per_page)

    # 페이지 선택
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 1

    col_prev, col_page, col_next = st.columns([1, 3, 1])

    with col_prev:
        if st.button("◀ 이전", disabled=(st.session_state['current_page'] == 1)):
            st.session_state['current_page'] -= 1
            st.rerun()

    with col_page:
        page = st.selectbox(
            "페이지",
            options=range(1, total_pages + 1),
            index=st.session_state['current_page'] - 1,
            key='page_selector'
        )
        if page != st.session_state['current_page']:
            st.session_state['current_page'] = page
            st.rerun()

    with col_next:
        if st.button("다음 ▶", disabled=(st.session_state['current_page'] == total_pages)):
            st.session_state['current_page'] += 1
            st.rerun()

    # 현재 페이지 데이터
    start_idx = (st.session_state['current_page'] - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_df = df.iloc[start_idx:end_idx].copy()

    # 누락 여부 컬럼에 HTML 스타일 적용
    def style_status(status):
        if status == '정상':
            return '<div class="status-normal">정상</div>'
        elif status == '정상 (전체)':
            return '<div class="status-normal-full">정상 (전체)</div>'
        elif status == '누락':
            return '<div class="status-missing">누락</div>'
        else:
            return status

    page_df['누락 여부'] = page_df['누락 여부'].apply(style_status)

    # 테이블을 HTML로 변환하여 표시
    st.markdown(f"**{start_idx + 1}-{min(end_idx, len(df))} / {len(df)}개 표시**")

    # 테이블 표시 (더 넓은 width)
    st.markdown('<div style="width: 100%; overflow-x: auto;">', unsafe_allow_html=True)

    # HTML 테이블 생성
    html_table = '<table style="width: 100%; border-collapse: collapse;">'
    html_table += '<thead><tr style="background-color: #f0f2f6;">'
    html_table += '<th style="padding: 10px; border: 1px solid #ddd; text-align: center;">번호</th>'
    html_table += '<th style="padding: 10px; border: 1px solid #ddd; text-align: left; min-width: 300px;">제목</th>'
    html_table += '<th style="padding: 10px; border: 1px solid #ddd; text-align: center; min-width: 200px;">발행일</th>'
    html_table += '<th style="padding: 10px; border: 1px solid #ddd; text-align: center; min-width: 100px;">누락 여부</th>'
    html_table += '<th style="padding: 10px; border: 1px solid #ddd; text-align: center; min-width: 100px;">URL</th>'
    html_table += '</tr></thead><tbody>'

    for _, row in page_df.iterrows():
        html_table += '<tr>'
        html_table += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{row["번호"]}</td>'
        html_table += f'<td style="padding: 10px; border: 1px solid #ddd;">{row["제목"]}</td>'
        html_table += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{row["발행일"]}</td>'
        html_table += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{row["누락 여부"]}</td>'
        html_table += f'<td style="padding: 10px; border: 1px solid #ddd; text-align: center;"><a href="{row["URL"]}" target="_blank">링크</a></td>'
        html_table += '</tr>'

    html_table += '</tbody></table>'
    st.markdown(html_table, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # CSV 다운로드
    st.markdown("---")
    csv = df.copy()
    csv['누락 여부'] = st.session_state['results']  # 원본 데이터의 누락 여부 복원
    csv = pd.DataFrame(st.session_state['results']).to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 전체 결과 CSV 다운로드",
        data=csv,
        file_name=f"{blog_id}_indexing_check_v2.csv",
        mime="text/csv"
    )
