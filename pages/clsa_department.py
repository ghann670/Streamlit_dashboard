import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt

# ✅ 데이터 불러오기 및 필터링
df_all = pd.read_csv("df_all.csv", parse_dates=["created_at"])
df_clsa = df_all[df_all['organization'] == 'CLSA'].copy()

# ✅ 파생 컬럼 생성
df_clsa['day_bucket'] = df_clsa['created_at'].dt.date
df_clsa['week_bucket'] = df_clsa['created_at'].dt.to_period('W').astype(str)
df_clsa['agent_type'] = df_clsa['function_mode'].str.split(":").str[0]
df_clsa['saved_minutes'] = df_clsa['agent_type'].map({
    "deep_research": 40, "pulse_check": 30
}).fillna(30)

# ✅ 페이지 설정
st.set_page_config(page_title="CLSA Usage Dashboard", layout="wide")
st.title("🏢 CLSA Department Usage Dashboard")

# ✅ division 선택
divisions = sorted(df_clsa['division'].dropna().unique())
selected_div = st.selectbox("Select Division", divisions)

# ✅ division 기준 필터링
df_div = df_clsa[df_clsa['division'] == selected_div]

# ✅ Summary
st.markdown("### 🔢 Division Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total Events", df_div.shape[0])
col2.metric("Active Users", df_div['user_email'].nunique())
col3.metric("Avg Saved Time", f"{df_div['saved_minutes'].mean():.1f} min")

# ✅ 일별 트렌드 + 피벗 테이블
st.markdown("---")
st.markdown("### 📅 Daily Event Trend and Function Breakdown")

# 1. 날짜 및 기능별 집계
df_div['day_bucket'] = pd.to_datetime(df_div['created_at']).dt.date
df_day = df_div.groupby(['day_bucket', 'agent_type']).size().reset_index(name='count')

# 2. 누락 조합 채우기
all_dates = pd.date_range(df_day['day_bucket'].min(), df_day['day_bucket'].max()).date
all_agents = df_day['agent_type'].unique()
full_index = pd.MultiIndex.from_product([all_dates, all_agents], names=['day_bucket', 'agent_type'])
df_day = pd.merge(full_index.to_frame(index=False), df_day, how='left', on=['day_bucket', 'agent_type'])
df_day['count'] = df_day['count'].fillna(0).astype(int)
df_day['day_label'] = pd.to_datetime(df_day['day_bucket']).dt.strftime('%m-%d')

# 3. 정렬
agent_order = df_day.groupby('agent_type')['count'].sum().sort_values(ascending=False).index.tolist()
df_day['agent_type'] = pd.Categorical(df_day['agent_type'], categories=agent_order, ordered=True)
df_day = df_day.sort_values(['day_label', 'agent_type'])

# 4. 시각화 + 피벗 테이블
left, right = st.columns([6, 6])

with left:
    fig = px.line(
        df_day.groupby('day_bucket').sum().reset_index(),
        x='day_bucket',
        y='count',
        markers=True,
        title="📅 Daily Event Count in Division",
        labels={"day_bucket": "Date", "count": "Events"}
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    df_pivot = df_day.pivot_table(
        index='agent_type',
        columns='day_label',
        values='count',
        aggfunc='sum',
        fill_value=0
    )
    df_pivot['Total'] = df_pivot.sum(axis=1)
    df_pivot = df_pivot[['Total'] + [col for col in df_pivot.columns if col != 'Total']]
    df_pivot.loc['Total'] = df_pivot.sum(numeric_only=True)
    st.dataframe(df_pivot.astype(int), use_container_width=True)

# ✅ 주간 기능 트렌드
st.markdown("---")
st.markdown("### 📈 Weekly Function Usage")

df_div['week'] = df_div['created_at'].dt.to_period("W").astype(str)
df_week_func = df_div.groupby(['week', 'agent_type']).size().reset_index(name='count')

chart = alt.Chart(df_week_func).mark_line(point=True).encode(
    x='week:N',
    y='count:Q',
    color='agent_type:N',
    tooltip=['week', 'agent_type', 'count']
).properties(width=900, height=300)

st.altair_chart(chart, use_container_width=True)

