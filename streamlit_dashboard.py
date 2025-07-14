import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt

# Load dataset
df_all = pd.read_csv("df_all.csv", parse_dates=["created_at"])

# 기준 날짜: 오늘 날짜 정오 기준
now = pd.Timestamp.now().normalize() + pd.Timedelta(hours=12)

# 각 주차 범위 설정: 7일씩 고정
week_ranges = {
    'week4': (now - pd.Timedelta(days=6), now),
    'week3': (now - pd.Timedelta(days=13), now - pd.Timedelta(days=7)),
    'week2': (now - pd.Timedelta(days=20), now - pd.Timedelta(days=14)),
    'week1': (now - pd.Timedelta(days=27), now - pd.Timedelta(days=21)),
}

# 각 row에 대해 week_bucket 할당
def assign_week_bucket(date):
    for week, (start, end) in week_ranges.items():
        if start <= date <= end:
            return week
    return None

df_all['week_bucket'] = df_all['created_at'].apply(assign_week_bucket)
df_all['day_bucket'] = df_all['created_at'].dt.date
df_all['agent_type'] = df_all['function_mode'].str.split(":").str[0]

# 절감 시간 매핑
time_map = {"deep_research": 40, "pulse_check": 30}
df_all["saved_minutes"] = df_all["agent_type"].map(time_map).fillna(30)

# Streamlit UI
st.set_page_config(page_title="Usage Summary Dashboard", layout="wide")
st.title("🚀 Usage Summary Dashboard")

# 조직 선택 필터
org_list = df_all['organization'].dropna().unique()
selected_org = st.selectbox("Select Organization", sorted(org_list))

# 조직별 데이터 필터링
df_org = df_all[df_all['organization'] == selected_org]
df_active = df_org[df_org['status'] == 'active']

# 빅넘버 계산
total_events = df_active.shape[0]
total_users = df_org['user_email'].nunique()
active_users = df_active['user_email'].nunique()
active_ratio = f"{active_users} / {total_users}"

# Top user
if not df_active['user_name'].dropna().empty:
    top_user = df_active['user_name'].value_counts().idxmax()
    top_user_count = df_active['user_name'].value_counts().max()
    top_user_display = f"{top_user} ({top_user_count} times)"
else:
    top_user_display = "N/A"

# 평균 사용자당 사용량
avg_events = round(total_events / active_users, 1) if active_users > 0 else 0

# 주당 절감 시간 계산
used_weeks = df_org["week_bucket"].dropna().nunique()
if used_weeks >= 1 and active_users > 0:
    total_saved_minutes = df_active["saved_minutes"].sum()
    saved_minutes_per_user_per_week = round(total_saved_minutes / used_weeks / active_users, 1)
    saved_display = f"{saved_minutes_per_user_per_week} min"
else:
    saved_display = "—"

# Inactive Users 계산
inactive_emails = df_org[~df_org['user_email'].isin(df_active['user_email'])]['user_email'].dropna().unique()
inactive_display = ", ".join(inactive_emails) if len(inactive_emails) > 0 else "—"

# Layout – Metrics
col1, col2, col3 = st.columns(3)
col1.metric("All Events", total_events)
col2.metric("Active / Total Users", active_ratio)
col3.metric("Top User", top_user_display)

col4, col5, col6 = st.columns(3)
col4.metric("Avg. Events per Active User", avg_events)
col5.metric("Avg. Time Saved / User / Week", saved_display)
with col6:
    st.markdown("**Inactive Users**")
    st.markdown(
        f"""
        <div style='
            max-height: 80px;
            overflow-y: auto;
            font-size: 13px;
            border: 1px solid #ccc;
            padding: 6px;
            border-radius: 5px;
            background-color: #f9f9f9;
        '>
            {inactive_display}
        </div>
        """,
        unsafe_allow_html=True
    )

# Total usage 시계열 차트 (Plotly로 변경)
st.markdown("---")
st.subheader("📅 Total Usage Over Time (All Functions)")

# 날짜별 전체 사용량 집계
df_active_org = df_active.copy().sort_values("created_at")
df_active_org["count"] = 1
df_total_daily = df_active_org.groupby(df_active_org["created_at"].dt.date).size().reset_index(name="count")
df_total_daily["created_at"] = pd.to_datetime(df_total_daily["created_at"])

# 날짜 레이블 (예: "7/14")
df_total_daily["date_label"] = df_total_daily["created_at"].dt.strftime("%-m/%d")

# Plotly 라인차트
fig1 = px.line(
    df_total_daily,
    x="date_label",
    y="count",
    markers=True,
    labels={"date_label": "Date", "count": "Total Event Count"},
)
fig1.update_layout(height=300, width=900, xaxis_tickangle=0)
st.plotly_chart(fig1, use_container_width=True)


# ✅ New Section: 유저별 라인차트 추가
st.markdown("### 👥 Users' Daily Usage")

# 유저별 일별 사용량 집계
df_user_daily = df_active_org.groupby([df_active_org["created_at"].dt.date, "user_name"]).size().reset_index(name="count")
df_user_daily["created_at"] = pd.to_datetime(df_user_daily["created_at"])
df_user_daily["date_label"] = df_user_daily["created_at"].dt.strftime("%-m/%d")
df_user_daily.rename(columns={"user_name": "user"}, inplace=True)

# ✅ 유저별 total usage 수 기준 정렬
user_total_counts = df_user_daily.groupby("user")["count"].sum()
sorted_users = user_total_counts.sort_values(ascending=False).index.tolist()
default_users = sorted_users[:3]  # 상위 5명 자동 선택

# ✅ 멀티셀렉트 (전체 유저 포함, 정렬된 순서, 상위 5명 기본 선택)
selected_users = st.multiselect(
    "Select users to display",
    options=sorted_users,
    default=default_users
)

# ✅ 필터링된 유저 데이터
df_user_filtered = df_user_daily[df_user_daily["user"].isin(selected_users)]

# ✅ 라인차트 시각화
if df_user_filtered.empty:
    st.info("No data for selected users.")
else:
    chart_users = alt.Chart(df_user_filtered).mark_line(point=True).encode(
        x=alt.X("date_label:N", title="Date", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("count:Q", title="Event Count"),
        color=alt.Color("user:N", title="User"),
        tooltip=["user", "count"]
    ).properties(width=900, height=300)

    st.altair_chart(chart_users, use_container_width=True)


# 함수 및 주간 시계열
st.markdown("---")
st.subheader("📈 Weekly Function Usage Trends")

df_chart = df_org.groupby(['week_bucket', 'agent_type']).size().reset_index(name='count')

# 누락된 week_bucket, agent_type 조합 채워넣기
all_weeks = list(week_ranges.keys())
all_agents = df_chart['agent_type'].unique()
all_combinations = pd.MultiIndex.from_product([all_weeks, all_agents], names=['week_bucket', 'agent_type']).to_frame(index=False)
df_chart = pd.merge(all_combinations, df_chart, on=['week_bucket', 'agent_type'], how='left')
df_chart['count'] = df_chart['count'].fillna(0).astype(int)

# Pivot Table
df_week_table = df_chart.pivot_table(
    index='agent_type',
    columns='week_bucket',
    values='count',
    fill_value=0,
    aggfunc='sum'
)
df_week_table['Total'] = df_week_table.sum(axis=1)
df_week_table = df_week_table.sort_values('Total', ascending=False)
df_week_table = df_week_table[['Total'] + [col for col in df_week_table.columns if col != 'Total']]
df_week_table.loc['Total'] = df_week_table.sum(numeric_only=True)

sorted_agent_order = df_week_table.drop("Total").index.tolist()
df_chart['agent_type'] = pd.Categorical(df_chart['agent_type'], categories=sorted_agent_order, ordered=True)
df_chart = df_chart.sort_values('agent_type')

left, right = st.columns([6, 6])
with left:
    chart_week = alt.Chart(df_chart).mark_line(point=True).encode(
        x=alt.X('week_bucket:N', title='Week', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('count:Q', title='Event Count'),
        color=alt.Color('agent_type:N', title='Function', sort=sorted_agent_order),
        tooltip=['agent_type', 'count']
    ).properties(width=600, height=300)

    st.altair_chart(chart_week, use_container_width=True)

with right:
    st.dataframe(df_week_table.astype(int), use_container_width=True)



# 📊 Daily usage 시계열
st.subheader("📊 Daily Function Usage for a Selected Week")

# 📅 주차 선택
week_options = sorted(df_all['week_bucket'].dropna().unique(), reverse=True)
selected_week = st.selectbox("Select Week", week_options, key="daily_select_week")
week_start, week_end = week_ranges[selected_week]
week_dates = pd.date_range(week_start, week_end).date

# 📆 선택된 주간 데이터 필터링
df_week = df_org[df_org['created_at'].dt.date.isin(week_dates)]

# 📊 일별-기능별 집계
agent_types = df_week['agent_type'].unique()
all_combinations = pd.MultiIndex.from_product(
    [week_dates, agent_types],
    names=['day_bucket', 'agent_type']
).to_frame(index=False)

df_day = df_week.groupby(['day_bucket', 'agent_type']).size().reset_index(name='count')
df_day = pd.merge(all_combinations, df_day, on=['day_bucket', 'agent_type'], how='left')
df_day['count'] = df_day['count'].fillna(0).astype(int)

# ✅ 날짜 레이블 포맷 변경
df_day['day_label'] = pd.to_datetime(df_day['day_bucket']).dt.strftime('%m-%d')

# 📊 기능별 정렬 기준 계산 (많이 쓴 순서 → 아래층부터 쌓임)
agent_order_by_volume = (
    df_day.groupby('agent_type')['count']
    .sum()
    .sort_values(ascending=False)
    .index.tolist()
)
agent_order_for_stack = list(reversed(agent_order_by_volume))  # 역순으로 쌓기

# 🔁 정렬 순서 적용
df_day['agent_type'] = pd.Categorical(
    df_day['agent_type'],
    categories=agent_order_for_stack,
    ordered=True
)
df_day = df_day.sort_values(['day_label', 'agent_type'])

# 📈 Altair 차트 + 📋 테이블
left2, right2 = st.columns([6, 6])
with left2:
    chart_day = alt.Chart(df_day).mark_bar().encode(
        x=alt.X('day_label:N', title='Date', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('count:Q', title='Event Count', stack='zero'),
        color=alt.Color('agent_type:N', title='Function', sort=agent_order_for_stack),
        tooltip=['agent_type:N', 'count:Q']
    ).properties(width=600, height=300)

    st.altair_chart(chart_day, use_container_width=True)

with right2:
    # 📊 집계 테이블 준비
    df_day_table = df_day.pivot_table(
        index='agent_type',
        columns='day_label',
        values='count',
        fill_value=0,
        aggfunc='sum'
    )
    df_day_table['Total'] = df_day_table.sum(axis=1)
    df_day_table = df_day_table.sort_values('Total', ascending=False)
    df_day_table = df_day_table[['Total'] + [col for col in df_day_table.columns if col != 'Total']]
    df_day_table.loc['Total'] = df_day_table.sum(numeric_only=True)

    st.dataframe(df_day_table.astype(int), use_container_width=True)


# 👥 Function Usage by User (Stacked by Week)
st.subheader("👥 Function Usage by User (Stacked by Week)")

# 전체 유저-기능-주차별 집계
df_user_stack_all = df_org.groupby(['week_bucket', 'user_name', 'agent_type']).size().reset_index(name='count')

# Top 10 유저만 포함
top_users = df_user_stack_all.groupby('user_name')['count'].sum().nlargest(10).index.tolist()
df_user_stack_all = df_user_stack_all[df_user_stack_all['user_name'].isin(top_users)]

# 피벗 및 melt
df_user_pivot = df_user_stack_all.pivot_table(
    index=['week_bucket', 'user_name'],
    columns='agent_type',
    values='count',
    fill_value=0
).reset_index()

df_user_melted = df_user_pivot.melt(
    id_vars=['week_bucket', 'user_name'],
    var_name='agent_type',
    value_name='count'
)

# 기능 정렬 기준 정의
sorted_func_order = df_user_stack_all.groupby('agent_type')['count'].sum().sort_values(ascending=False).index.tolist()
df_user_melted['agent_type'] = pd.Categorical(df_user_melted['agent_type'], categories=sorted_func_order, ordered=True)

# 시각화
left, right = st.columns([7, 5])
with left:
    chart = alt.Chart(df_user_melted).mark_bar().encode(
        x=alt.X('user_name:N', title='User', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('count:Q', title='Usage Count', stack='zero'),
        color=alt.Color('agent_type:N', title='Function', sort=sorted_func_order),
        column=alt.Column('week_bucket:N', title='Week')
    ).properties(height=300, width=150)

    st.altair_chart(chart, use_container_width=True)

with right:
    df_table = df_user_stack_all.pivot_table(
        index='user_name',
        columns='agent_type',
        values='count',
        aggfunc='sum',
        fill_value=0
    )
    df_table['Total'] = df_table.sum(axis=1)
    df_table = df_table.sort_values('Total', ascending=False)
    df_table = df_table[['Total'] + [col for col in df_table.columns if col != 'Total']]

    st.dataframe(df_table.astype(int), use_container_width=True)
