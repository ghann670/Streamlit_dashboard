import streamlit as st
import pandas as pd
import plotly.express as px

# ✅ 데이터 불러오기 및 필터링
df_all = pd.read_csv("df_all.csv", parse_dates=["created_at"])
df_clsa = df_all[df_all['organization'] == 'CLSA'].copy()
df_clsa['day_bucket'] = df_clsa['created_at'].dt.date
df_clsa['week_bucket'] = df_clsa['created_at'].dt.to_period('W').astype(str)

# ✅ 주차 필터 설정
weeks = sorted(df_clsa['week_bucket'].dropna().unique())
selected_week = st.selectbox("📆 Select Week", weeks)
df_week = df_clsa[df_clsa['week_bucket'] == selected_week]

# ✅ 사용자 리스트 선택
user_list = sorted(df_week['user_name'].dropna().unique())
selected_users = st.multiselect("Select users to display", user_list, default=user_list[:3])

# ✅ 일별 사용자 이벤트 집계
df_filtered = df_week[df_week['user_name'].isin(selected_users)]
df_user_day = df_filtered.groupby(['day_bucket', 'user_name']).size().reset_index(name='count')

# ✅ 시각화: 유저별 라인차트
st.markdown("### 👥 Users' Daily Usage")
fig = px.line(
    df_user_day,
    x="day_bucket",
    y="count",
    color="user_name",
    markers=True,
    labels={"day_bucket": "Date", "count": "Event Count", "user_name": "User"},
    title="👤 Daily Usage per User"
)
st.plotly_chart(fig, use_container_width=True)

# ✅ 피벗 테이블: 일별 total usage
st.markdown("### 📊 Daily Total Usage Table")
df_total = df_week.groupby('day_bucket').size().reset_index(name='total_events')
df_total['day_label'] = pd.to_datetime(df_total['day_bucket']).dt.strftime('%m-%d')
df_pivot = df_total.set_index('day_label').T
st.dataframe(df_pivot, use_container_width=True)