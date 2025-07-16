import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

# ✅ 페이지 설정
st.set_page_config(page_title="CLSA Usage Dashboard", layout="wide")
st.title("📊 CLSA Department Dashboard")

# ✅ 데이터 불러오기
df_all = pd.read_csv("df_all.csv", parse_dates=["created_at"])
df_clsa = df_all[df_all['organization'] == 'CLSA'].copy()

# ✅ 파생 컬럼
df_clsa['day_bucket'] = df_clsa['created_at'].dt.date
df_clsa['week_bucket'] = df_clsa['created_at'].dt.to_period('W').astype(str)
df_clsa['agent_type'] = df_clsa['function_mode'].str.split(":").str[0]
df_clsa['saved_minutes'] = df_clsa['agent_type'].map({
    "deep_research": 40, "pulse_check": 30
}).fillna(30)

# ✅ division 필터
divisions = sorted(df_clsa['division'].dropna().unique())
selected_div = st.selectbox("Select Division", divisions)
df_div = df_clsa[df_clsa['division'] == selected_div].copy()

# ✅ 사용자의 현재 날짜 기준 주차 범위 생성
now = pd.Timestamp.now().normalize() + pd.Timedelta(hours=12)
week_ranges = {
    'week4': (now - pd.Timedelta(days=6), now),
    'week3': (now - pd.Timedelta(days=13), now - pd.Timedelta(days=7)),
    'week2': (now - pd.Timedelta(days=20), now - pd.Timedelta(days=14)),
    'week1': (now - pd.Timedelta(days=27), now - pd.Timedelta(days=21)),
}

# ──────────────────────────────────────────────────────────────
# 👥 Users' Daily Usage
# ──────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("👥 Users' Daily Usage")

# ✅ 주차 선택 필터
week_options = list(week_ranges.keys())
selected_week = st.selectbox("Select Week", week_options)
week_start, week_end = week_ranges[selected_week]
week_dates = pd.date_range(week_start, week_end).date

# ✅ 선택한 주차 필터링
df_week = df_clsa[df_clsa['created_at'].dt.date.isin(week_dates)].copy()
df_week['date_label'] = df_week['created_at'].dt.strftime('%-m/%d')
df_week['user'] = df_week['user_name']

# ✅ 유저 정렬 및 기본 선택 (상위 3명)
user_total_counts = df_week.groupby('user')['user_email'].count()
sorted_users = user_total_counts.sort_values(ascending=False).index.tolist()
default_users = sorted_users[:3]

# ✅ 세션 상태로 멀티셀렉트 상태 관리
if "selected_users" not in st.session_state:
    st.session_state.selected_users = default_users

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("✅ 전체 선택"):
        st.session_state.selected_users = sorted_users
with col2:
    if st.button("❌ 전체 해제"):
        st.session_state.selected_users = []

selected_users = st.multiselect(
    "Select users to display",
    options=sorted_users,
    default=[u for u in st.session_state.selected_users if u in sorted_users],
    key="selected_users"
)

# ✅ 유저별 라인차트
df_chart = df_week[df_week['user'].isin(selected_users)]
df_chart = df_chart.groupby(['date_label', 'user']).size().reset_index(name='count')

if df_chart.empty:
    st.info("No data for selected users.")
else:
    line = alt.Chart(df_chart).mark_line(point=True).encode(
        x=alt.X("date_label:N", title="Date", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("count:Q", title="Event Count"),
        color=alt.Color("user:N", title="User"),
        tooltip=["user", "count"]
    ).properties(width=900, height=300)
    st.altair_chart(line, use_container_width=True)

# ✅ 일별 전체 사용량 피벗 테이블
df_total_daily = df_week.groupby(df_week['created_at'].dt.date).size().reset_index(name="count")
df_total_daily["day_label"] = df_total_daily["created_at"].dt.strftime("%-m/%d")
df_total_daily.set_index("day_label", inplace=True)g

# 📌 주차 내 모든 날짜 채워넣기
all_labels = pd.Series(week_dates).dt.strftime("%-m/%d").tolist()
for date in all_labels:
    if date not in df_total_daily.index:
        df_total_daily.loc[date] = 0

df_total_daily = df_total_daily.sort_index()
df_pivot = pd.DataFrame(df_total_daily.T)
df_pivot.index = ["Total"]
df_pivot = df_pivot.astype(int)

st.dataframe(df_pivot, use_container_width=True)
