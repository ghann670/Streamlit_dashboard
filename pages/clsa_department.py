import streamlit as st
import pandas as pd

st.set_page_config(page_title="CLSA", page_icon="📈")  # ✅ 여기만 바꾸면 사이드바 메뉴명 바뀜



# 데이터 로딩 및 전처리
df_all = pd.read_csv("df_all.csv", parse_dates=["created_at"])
df_clsa = df_all[df_all["organization"] == "CLSA"].copy()

# 📌 파생 컬럼
df_clsa["function_mode"] = df_clsa["function_mode"].fillna("unknown")
df_clsa["user_name"] = df_clsa["user_name"].fillna("unknown")
df_clsa["created_date"] = df_clsa["created_at"].dt.date

# 📅 기준 날짜: 오늘 정오
now = pd.Timestamp.now().normalize() + pd.Timedelta(hours=12)

# 📅 주차 버킷 설정
week_ranges = {
    "week4": (now - pd.Timedelta(days=6), now),
    "week3": (now - pd.Timedelta(days=13), now - pd.Timedelta(days=7)),
    "week2": (now - pd.Timedelta(days=20), now - pd.Timedelta(days=14)),
    "week1": (now - pd.Timedelta(days=27), now - pd.Timedelta(days=21)),
}

def assign_week(date):
    for week, (start, end) in week_ranges.items():
        if start <= date <= end:
            return week
    return None

df_clsa["week"] = df_clsa["created_at"].apply(assign_week)

# ✅ division 선택
st.set_page_config(page_title="CLSA Function Summary", layout="wide")
st.title("🏢 CLSA Function Usage Summary")

divisions = sorted(df_clsa["division"].dropna().unique())
selected_div = st.selectbox("Select Division", divisions)

# ✅ 부서 필터링
df_div = df_clsa[df_clsa["division"] == selected_div].copy()

# ✅ 유저 선택 필터
users = sorted(df_div["user_name"].dropna().unique())
default_users = users[:3]

if "selected_users" not in st.session_state:
    st.session_state.selected_users = default_users

selected_users = st.multiselect(
    "Select Users",
    options=users,
    default=[u for u in st.session_state.selected_users if u in users],
    key="selected_users"
)

# ✅ 선택된 유저 데이터
df_filtered = df_div[df_div["user_name"].isin(selected_users)].copy()

# 📊 피벗 테이블 생성
pivot_df = (
    df_filtered.groupby(["function_mode", "week"])
    .size()
    .reset_index(name="count")
    .pivot_table(index="function_mode", columns="week", values="count", fill_value=0)
)

# ✅ 열 순서 정리 및 Total 열 추가
ordered_cols = ["week1", "week2", "week3", "week4"]
for w in ordered_cols:
    if w not in pivot_df.columns:
        pivot_df[w] = 0
pivot_df = pivot_df[ordered_cols]
pivot_df["Total"] = pivot_df.sum(axis=1)
pivot_df.loc["Total"] = pivot_df.sum(numeric_only=True)

# ✅ 출력
st.markdown("### 📋 Weekly Function Usage Table")
st.dataframe(pivot_df.astype(int), use_container_width=True)
