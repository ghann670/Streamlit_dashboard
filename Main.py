import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt


st.set_page_config(page_title="Main", page_icon="🚀", layout="wide")


# Load dataset
df_all = pd.read_csv("df_all.csv")


# Convert created_at to datetime
df_all['created_at'] = pd.to_datetime(df_all['created_at'])

# 기준 날짜: 오늘 날짜 정오 기준
now = pd.Timestamp.now().normalize() + pd.Timedelta(hours=12)

# 각 주차 범위 설정
week_ranges = {
    'week4': (now - pd.Timedelta(days=6), now),
    'week3': (now - pd.Timedelta(days=13), now - pd.Timedelta(days=7)),
    'week2': (now - pd.Timedelta(days=20), now - pd.Timedelta(days=14)),
    'week1': (now - pd.Timedelta(days=27), now - pd.Timedelta(days=21)),
}

# 주차 버킷 할당 함수
def assign_week_bucket(date):
    if pd.isna(date):
        return None
    for week, (start, end) in week_ranges.items():
        if start <= date <= end:
            return week
    return None

# 전처리
df_all['week_bucket'] = df_all['created_at'].apply(assign_week_bucket)
df_all['day_bucket'] = df_all['created_at'].dt.date
df_all['agent_type'] = df_all['function_mode'].str.split(":").str[0]

# 절감 시간 매핑
time_map = {"deep_research": 40, "pulse_check": 30}
df_all["saved_minutes"] = df_all["agent_type"].map(time_map).fillna(30)

# UI 설정
st.title("\U0001F680 Usage Summary Dashboard")

# 조직 리스트 추출
org_event_counts = (
    df_all[df_all['status'] == 'active']
    .groupby('organization')
    .size()
    .sort_values(ascending=False)
)
org_list_sorted = org_event_counts.index.tolist()

# 조직 선택
selected_org = st.selectbox("Select Organization", org_list_sorted)

# 데이터 필터링
df_org = df_all[df_all['organization'] == selected_org]
df_active = df_org[df_org['status'] == 'active']

# Metric 계산
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

# 평균 이벤트
avg_events = round(total_events / active_users, 1) if active_users > 0 else 0

# 절감 시간
used_weeks = df_org["week_bucket"].dropna().nunique()
if used_weeks >= 1 and active_users > 0:
    total_saved_minutes = df_active["saved_minutes"].sum()
    saved_minutes_per_user_per_week = round(total_saved_minutes / used_weeks / active_users, 1)
    saved_display = f"{saved_minutes_per_user_per_week} min"
else:
    saved_display = "—"

# ✅ Invited & No-Usage Users 추출
invited_emails = df_org[df_org['status'] == 'invited_not_joined']['user_email'].dropna().unique()
joined_no_usage_emails = df_org[df_org['status'] == 'joined_no_usage']['user_email'].dropna().unique()

invited_display = ", ".join(invited_emails) if len(invited_emails) > 0 else "—"
joined_display = ", ".join(joined_no_usage_emails) if len(joined_no_usage_emails) > 0 else "—"

# Layout – Metrics
col1, col2, col3 = st.columns(3)
col1.metric("All Events", total_events)
col2.metric("Active / Total Users", active_ratio)
col3.metric("Top User", top_user_display)

col4, col5, col6 = st.columns(3)
earnings_users = df_org[df_org['earnings'] == 'onboarded']['user_email'].nunique()
briefing_users = df_org[df_org['briefing'] == 'onboarded']['user_email'].nunique()
col4.metric("Earnings/Briefing Users", f"{earnings_users}/{briefing_users}")
col5.metric("Avg. Events per Active User", avg_events)
col6.metric("Avg. Time Saved / User / Week", saved_display)

# Invited & No-Usage Users 표시
st.markdown("### 👥 User Status")
st.markdown("**Invited but Not Joined**")
st.markdown(
    f"""
    <div style='
        max-height: 60px;
        overflow-y: auto;
        font-size: 13px;
        border: 1px solid #ccc;
        padding: 6px;
        border-radius: 5px;
        background-color: #fffaf5;
    '>
        {invited_display}
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("**Joined but No Usage**")
st.markdown(
    f"""
    <div style='
        max-height: 60px;
        overflow-y: auto;
        font-size: 13px;
        border: 1px solid #ccc;
        padding: 6px;
        border-radius: 5px;
        background-color: #f5faff;
    '>
        {joined_display}
    </div>
    """,
    unsafe_allow_html=True
)



# Total usage 시계열 차트
st.markdown("---")
st.subheader("📅 Total Usage Over Time (All Functions)")

# 1️⃣ 날짜별 전체 사용량 집계
df_active_org = df_active.copy().sort_values("created_at")
df_active_org["count"] = 1
df_total_daily = df_active_org.groupby(df_active_org["created_at"].dt.date).size().reset_index(name="count")
df_total_daily["created_at"] = pd.to_datetime(df_total_daily["created_at"])

# ✅ 2️⃣ 날짜 라벨 생성 (예: 7/11)
df_total_daily["date_label"] = df_total_daily["created_at"].dt.strftime("%-m/%d")  # macOS/Linux
# 윈도우는 "%#m/%d"

# ✅ Plotly 시계열 차트 (y축 상단 여유 포함)
fig1 = px.line(
    df_total_daily,
    x="date_label",
    y="count",
    markers=True,
    labels={"date_label": "Date", "count": "Total Event Count"},
)
fig1.update_layout(height=300, width=900)

# ✅ y축 범위 자동보다 조금 더 크게 설정
max_count = df_total_daily["count"].max()
fig1.update_yaxes(range=[0, max_count + 10])

st.plotly_chart(fig1, use_container_width=True)



# ✅ New Section: 유저별 라인차트 추가
st.markdown("### 👥 Users' Daily Usage")

# 유저별 일별 사용량 집계
df_user_daily = df_active_org.groupby(
    [df_active_org["created_at"].dt.date, "user_name"]
).size().reset_index(name="count")

df_user_daily["created_at"] = pd.to_datetime(df_user_daily["created_at"])
df_user_daily["date_label"] = df_user_daily["created_at"].dt.strftime("%-m/%d")
df_user_daily.rename(columns={"user_name": "user"}, inplace=True)

# ✅ 유저별 total usage 수 기준 정렬
user_total_counts = df_user_daily.groupby("user")["count"].sum()
sorted_users = user_total_counts.sort_values(ascending=False).index.tolist()
default_users = sorted_users[:3]  # 상위 3명 기본 선택

# ✅ 세션 상태에 선택 유저 목록 저장
if "selected_users" not in st.session_state:
    st.session_state.selected_users = default_users

# ✅ 전체 선택 / 해제 버튼
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("✅ 전체 선택"):
        st.session_state.selected_users = sorted_users
with col2:
    if st.button("❌ 전체 해제"):
        st.session_state.selected_users = []

# ✅ 멀티셀렉트 (세션 상태로 동기화, 유효성 보정)
valid_default_users = [user for user in st.session_state.selected_users if user in sorted_users]

selected_users = st.multiselect(
    "Select users to display",
    options=sorted_users,
    default=valid_default_users,
    key="selected_users"
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
df_day = df_day.sort_values(['day_label', 'agent_type'], ascending = [True, True])

# 📈 Plotly 차트 + 📋 테이블
left2, right2 = st.columns([6, 6])
with left2:
    # 📊 Plotly stacked bar chart
    fig_day = px.bar(
        df_day,
        x="day_label",
        y="count",
        color="agent_type",
        category_orders={"agent_type": agent_order_for_stack},
        color_discrete_sequence=px.colors.qualitative.Set1,
        labels={"day_label": "Date", "count": "Event Count", "agent_type": "Function"},
    )
    fig_day.update_layout(
        barmode="stack",
        width=600,
        height=300,
        xaxis_title="Date",
        yaxis_title="Event Count",
        legend_title="Function",
    )
    st.plotly_chart(fig_day, use_container_width=True)

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

# 📅 주차 선택
week_options_user = sorted(df_org['week_bucket'].dropna().unique(), reverse=True)
selected_week_user = st.selectbox("Select Week", week_options_user, key="user_week_select")

# ✅ 선택된 주차만 필터링
df_user_week = df_org[df_org['week_bucket'] == selected_week_user]

# 전체 유저-기능 집계
df_user_stack_full = df_user_week.groupby(['user_name', 'agent_type']).size().reset_index(name='count')

# 👉 기능 정렬 기준 정의 (많이 쓴 순)
sorted_func_order = (
    df_user_stack_full.groupby('agent_type')['count']
    .sum().sort_values(ascending=False).index.tolist()
)

# ✅ 왼쪽: 차트용 - top 10 유저만 필터링
top_users = (
    df_user_stack_full.groupby('user_name')['count']
    .sum().nlargest(10).index.tolist()
)
df_user_stack_chart = df_user_stack_full[df_user_stack_full['user_name'].isin(top_users)].copy()
df_user_stack_chart['agent_type'] = pd.Categorical(
    df_user_stack_chart['agent_type'],
    categories=sorted_func_order,
    ordered=True
)
df_user_stack_chart = df_user_stack_chart.sort_values(['user_name', 'agent_type'])

# ✅ 오른쪽: 테이블용 - 전체 유저 포함
df_user_stack_full['agent_type'] = pd.Categorical(
    df_user_stack_full['agent_type'],
    categories=sorted_func_order,
    ordered=True
)

# 📊 시각화
left, right = st.columns([7, 5])
with left:
    fig = px.bar(
        df_user_stack_chart,
        x="user_name",
        y="count",
        color="agent_type",
        category_orders={
            "agent_type": sorted_func_order,
            "user_name": top_users
        },
        color_discrete_sequence=px.colors.qualitative.Set1,
        labels={"user_name": "User", "count": "Usage Count", "agent_type": "Function"},
    )
    fig.update_layout(
        barmode="stack",
        xaxis_title="User",
        yaxis_title="Usage Count",
        legend_title="Function",
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    df_user_table = df_user_stack_full.pivot_table(
        index='user_name',
        columns='agent_type',
        values='count',
        aggfunc='sum',
        fill_value=0
    )
    df_user_table['Total'] = df_user_table.sum(axis=1)
    df_user_table = df_user_table.sort_values('Total', ascending=False)
    df_user_table = df_user_table[['Total'] + [col for col in df_user_table.columns if col != 'Total']]

    st.dataframe(df_user_table.astype(int), use_container_width=True)


# 📊 Response Time Analysis
st.markdown("---")
st.subheader("📈 AI Response Time Analysis")

# 데이터 전처리
df_time = df_all.copy()
# 이상치 처리
df_time.loc[df_time['time_to_first_byte'] <= 0, 'time_to_first_byte'] = None
df_time.loc[df_time['time_to_first_byte'] > 300000, 'time_to_first_byte'] = None  # 5분 초과 제거

# ms를 초로 변환
df_time['time_to_first_byte'] = df_time['time_to_first_byte'] / 1000

# 기본 통계량 표시
col1, col2, col3 = st.columns(3)
with col1:
    median_time = df_time['time_to_first_byte'].median()
    st.metric("Median Response Time", f"{median_time:.1f} sec")
with col2:
    mean_time = df_time['time_to_first_byte'].mean()
    st.metric("Average Response Time", f"{mean_time:.1f} sec")
with col3:
    p95_time = df_time['time_to_first_byte'].quantile(0.95)
    st.metric("95th Percentile", f"{p95_time:.1f} sec")

# 시계열 그래프 (전체 너비)
df_time['date'] = df_time['created_at'].dt.date
daily_stats = df_time.groupby('date')['time_to_first_byte'].median().reset_index()

fig1 = px.line(daily_stats, x='date', y='time_to_first_byte',
               title='Daily Median Response Time',
               labels={'time_to_first_byte': 'Response Time (seconds)', 'date': 'Date'})

fig1.update_layout(
    height=400,
    hovermode='x unified'
)
st.plotly_chart(fig1, use_container_width=True)

# 두 번째 줄: 히스토그램과 도표
left_col, right_col = st.columns([3, 2])  # 히스토그램이 더 넓게

with left_col:
    # 히스토그램
    fig2 = px.histogram(
        df_time,
        x='time_to_first_byte',
        nbins=50,
        title='Distribution of Response Times',
        labels={'time_to_first_byte': 'Response Time (seconds)', 'count': 'Number of Requests'}
    )
    
    # 중앙값과 평균값 표시선 추가
    fig2.add_vline(
        x=median_time,
        line=dict(color="red", width=2, dash="dash"),
        annotation_text=f"Median: {median_time:.1f}s",
        annotation_position="top",
        annotation=dict(font=dict(color="red"))
    )
    fig2.add_vline(
        x=mean_time,
        line=dict(color="green", width=2, dash="dash"),
        annotation_text=f"Mean: {mean_time:.1f}s",
        annotation_position="bottom",
        annotation=dict(font=dict(color="green"))
    )
    
    fig2.update_layout(
        height=400,
        bargap=0.1,
        showlegend=True
    )
    st.plotly_chart(fig2, use_container_width=True)

with right_col:
    # 함수별 응답 시간 (Count 기준 내림차순 정렬)
    st.markdown("### 🔍 Response Time by Function")
    func_stats = df_time.groupby('agent_type')['time_to_first_byte'].agg([
        'mean', 'median', 'count'
    ]).reset_index()
    func_stats.columns = ['Function', 'Mean (sec)', 'Median (sec)', 'Count']
    func_stats = func_stats.sort_values('Count', ascending=False)  # Count 기준 내림차순
    st.dataframe(func_stats.round(2), use_container_width=True, hide_index=True)  # hide_index=True 추가
