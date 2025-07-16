import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

# ✅ 데이터 불러오기 및 필터링
df_all = pd.read_csv("df_all.csv", parse_dates=["created_at"])
df_clsa = df_all[df_all['organization'] == 'CLSA'].copy()


st.markdown("---")
st.subheader("👥 Users' Daily Usage")

# 기준 날짜: 오늘 날짜 정오 기준
now = pd.Timestamp.now().normalize() + pd.Timedelta(hours=12)

# ✅ 최근 4주 기준 주차 선택
week_ranges = {
    'week4': (now - pd.Timedelta(days=6), now),
    'week3': (now - pd.Timedelta(days=13), now - pd.Timedelta(days=7)),
    'week2': (now - pd.Timedelta(days=20), now - pd.Timedelta(days=14)),
    'week1': (now - pd.Timedelta(days=27), now - pd.Timedelta(days=21)),
}
week_options = list(week_ranges.keys())
selected_week = st.selectbox("Select Week", week_options)
week_start, week_end = week_ranges[selected_week]
week_dates = pd.date_range(week_start, week_end).date

# ✅ 필터링된 기간 & 유저
df_week = df_clsa[df_clsa['created_at'].dt.date.isin(week_dates)].copy()
df_week['date_label'] = df_week['created_at'].dt.strftime('%-m/%d')
df_week['user'] = df_week['user_name']

# ✅ 유저별 총 사용량 기준 정렬
user_total_counts = df_week.groupby('user')['user_email'].count()
sorted_users = user_total_counts.sort_values(ascending=False).index.tolist()
default_users = sorted_users[:3]

# ✅ 전체 선택/해제 + 멀티셀렉트
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("✅ 전체 선택"):
        st.session_state.selected_users = sorted_users
with col2:
    if st.button("❌ 전체 해제"):
        st.session_state.selected_users = []

# ✅ 멀티셀렉트 박스
if "selected_users" not in st.session_state:
    st.session_state.selected_users = default_users

selected_users = st.multiselect(
    "Select users to display",
    options=sorted_users,
    default=[u for u in st.session_state.selected_users if u in sorted_users],
    key="selected_users"
)

# ✅ 라인차트용 데이터
df_chart = df_week[df_week['user'].isin(selected_users)]
df_chart = df_chart.groupby(['date_label', 'user']).size().reset_index(name='count')

# ✅ 라인차트
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

# ✅ 피벗 테이블 (Total 기준)
df_total_daily = df_week.groupby(df_week['created_at'].dt.date).size().reset_index(name="count")
df_total_daily["day_label"] = df_total_daily["created_at"].dt.strftime("%-m/%d")
df_total_daily.set_index("day_label", inplace=True)

# 📌 모든 날짜 채우기
all_labels = pd.Series(week_dates).dt.strftime("%-m/%d").tolist()
for date in all_labels:
    if date not in df_total_daily.index:
        df_total_daily.loc[date] = 0

df_total_daily = df_total_daily.sort_index()
df_pivot = pd.DataFrame(df_total_daily.T)
df_pivot.index = ["Total"]
df_pivot = df_pivot.astype(int)

st.dataframe(df_pivot, use_container_width=True)
