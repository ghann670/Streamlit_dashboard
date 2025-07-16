import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt

# Load and filter CLSA data
df_all = pd.read_csv("df_all.csv", parse_dates=["created_at"])
df_clsa = df_all[df_all['organization'] == 'CLSA'].copy()

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

# ✅ division 리스트로 수정
divisions = sorted(df_clsa['division'].dropna().unique())
selected_div = st.selectbox("Select Division", divisions)

# ✅ division 기준 필터링
df_div = df_clsa[df_clsa['division'] == selected_div]

# Summary
st.markdown("### 🔢 Division Summary")

col1, col2, col3 = st.columns(3)
col1.metric("Total Events", df_div.shape[0])
col2.metric("Active Users", df_div['user_email'].nunique())
col3.metric("Avg Saved Time", f"{df_div['saved_minutes'].mean():.1f} min")

# 📈 Daily chart
df_daily = df_div.groupby(df_div["created_at"].dt.date).size().reset_index(name="count")
fig = px.line(
    df_daily,
    x="created_at",
    y="count",
    title="📅 Daily Event Count in Division",
    labels={"created_at": "Date", "count": "Events"},
    markers=True
)
st.plotly_chart(fig, use_container_width=True)

# 📊 Weekly usage by function
df_div['week'] = df_div['created_at'].dt.to_period("W").astype(str)
df_week_func = df_div.groupby(['week', 'agent_type']).size().reset_index(name='count')

chart = alt.Chart(df_week_func).mark_line(point=True).encode(
    x='week:N',
    y='count:Q',
    color='agent_type:N',
    tooltip=['week', 'agent_type', 'count']
).properties(width=900, height=300)

st.altair_chart(chart, use_container_width=True)

# 👤 Top users
df_user = df_div.groupby('user_name').size().reset_index(name='count')
df_user = df_user.sort_values('count', ascending=False).head(10)

bar = px.bar(
    df_user,
    x='user_name',
    y='count',
    title="👤 Top 10 Users by Event Count",
    labels={"user_name": "User", "count": "Events"}
)
st.plotly_chart(bar, use_container_width=True)
