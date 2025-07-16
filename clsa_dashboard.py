import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt

# Load and filter CLSA data
df_all = pd.read_csv("df_all.csv", parse_dates=["created_at"])
df_clsa = df_all[df_all['organization'] == 'clsa'].copy()

# 기본 파생 컬럼
df_clsa['day_bucket'] = df_clsa['created_at'].dt.date
df_clsa['week_bucket'] = pd.to_datetime(df_clsa['created_at']).dt.to_period('W').astype(str)
df_clsa['agent_type'] = df_clsa['function_mode'].str.split(":").str[0]
df_clsa['saved_minutes'] = df_clsa['agent_type'].map({
    "deep_research": 40, "pulse_check": 30
}).fillna(30)

# UI 구성
st.set_page_config(page_title="CLSA Usage Dashboard", layout="wide")
st.title("🏢 CLSA Department Usage Dashboard")

# 부서 리스트
departments = sorted(df_clsa['department'].dropna().unique())
selected_dept = st.selectbox("Select Department", departments)

df_dept = df_clsa[df_clsa['department'] == selected_dept]


st.markdown("### 🔢 Department Summary")

col1, col2, col3 = st.columns(3)
col1.metric("Total Events", df_dept.shape[0])
col2.metric("Active Users", df_dept['user_email'].nunique())
col3.metric("Avg Saved Time", f"{df_dept['saved_minutes'].mean():.1f} min")


df_daily = df_dept.groupby(df_dept["created_at"].dt.date).size().reset_index(name="count")

fig = px.line(
    df_daily,
    x="created_at",
    y="count",
    title="📅 Daily Event Count in Department",
    labels={"created_at": "Date", "count": "Events"},
    markers=True
)
st.plotly_chart(fig, use_container_width=True)


df_dept['week'] = df_dept['created_at'].dt.to_period("W").astype(str)
df_week_func = df_dept.groupby(['week', 'agent_type']).size().reset_index(name='count')

chart = alt.Chart(df_week_func).mark_line(point=True).encode(
    x='week:N',
    y='count:Q',
    color='agent_type:N',
    tooltip=['week', 'agent_type', 'count']
).properties(width=900, height=300)

st.altair_chart(chart, use_container_width=True)


df_user = df_dept.groupby('user_name').size().reset_index(name='count')
df_user = df_user.sort_values('count', ascending=False).head(10)

bar = px.bar(
    df_user,
    x='user_name',
    y='count',
    title="👤 Top 10 Users by Event Count",
    labels={"user_name": "User", "count": "Events"}
)
st.plotly_chart(bar, use_container_width=True)
