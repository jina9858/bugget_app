import streamlit as st
import pandas as pd
import calendar
import datetime as dt
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple

# 페이지 설정
st.set_page_config(page_title="예산 달력", layout="wide")

# --- 설정값 ---
YEAR = 2026
START_MONTH = 2
END_MONTH = 6
INCOME_FILE = "income_data.json"
FIXED_FILE = "fixed_events.json"

# -----------------------------
# 1. 데이터 관리 로직 (수입/고정비)
# -----------------------------
def load_income() -> Dict[str, int]:
    default_income = {f"{YEAR}-{m:02d}": 0 for m in range(START_MONTH, END_MONTH + 1)}
    default_income[f"{YEAR}-02"] = 4_400_000
    default_income[f"{YEAR}-03"] = 5_650_000
    if os.path.exists(INCOME_FILE):
        try:
            with open(INCOME_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return default_income
    return default_income

def save_income(income_dict: Dict[str, int]):
    with open(INCOME_FILE, "w", encoding="utf-8") as f:
        json.dump(income_dict, f, ensure_ascii=False, indent=2)

@dataclass(frozen=True)
class Event:
    date: dt.date
    category: str
    item: str
    amount: int
    note: str = ""

def build_fixed_events(year=YEAR, start_month=START_MONTH, end_month=END_MONTH) -> List[Event]:
    # (기존 고정비 데이터 생성 로직 동일...)
    events = []
    # ... 생략 (기존과 동일한 고정비 리스트) ...
    return events

def load_fixed_events() -> List[Event]:
    if os.path.exists(FIXED_FILE):
        try:
            with open(FIXED_FILE, "r", encoding="utf-8") as f:
                rows = json.load(f)
                return [Event(date=dt.date.fromisoformat(r["date"]), category=r["category"], item=r["item"], amount=r["amount"], note=r["note"]) for r in rows]
        except: pass
    return []

# -----------------------------
# 2. 세션 상태 관리
# -----------------------------
if "income_data" not in st.session_state:
    st.session_state.income_data = load_income()
if "fixed_events" not in st.session_state:
    st.session_state.fixed_events = load_fixed_events()
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["date", "category", "memo", "amount"])
    st.session_state.df["date"] = pd.to_datetime(st.session_state.df["date"])

# ---------- Sidebar ----------
st.sidebar.header("⚙️ 예산 및 설정")

selected_month = st.sidebar.selectbox("조회 월 선택", options=list(range(START_MONTH, END_MONTH + 1)), format_func=lambda m: f"{m}월")

# --- [추가] 카테고리별 예산 설정 ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 카테고리별 예산 설정")
food_budget = st.sidebar.number_input("🍔 식비 예산", min_value=0, value=650_000, step=10000)
em_budget = st.sidebar.number_input("🚨 예비비 예산", min_value=0, value=200_000, step=10000)

# --- 수입/고정비 편집 (생략 가능하지만 유지) ---
with st.sidebar.expander("💰 수입 수정"):
    income_df = pd.DataFrame([{"월": k, "수입(원)": v} for k, v in st.session_state.income_data.items()])
    edited_inc = st.data_editor(income_df, use_container_width=True, hide_index=True)
    if st.button("수입 저장"):
        st.session_state.income_data = dict(zip(edited_inc["월"], edited_inc["수입(원)"]))
        save_income(st.session_state.income_data)
        st.rerun()

# ---------- Main ----------
st.title(f"📅 {YEAR}년 {selected_month}월 예산 달력")

# 지출 입력
with st.expander("➕ 지출 추가", expanded=True):
    c1, c2, c3, c4 = st.columns([1.2, 1.0, 2.0, 1.0])
    with c1: d = st.date_input("날짜", value=dt.date(YEAR, selected_month, 1))
    with c2: cat = st.selectbox("분류", ["식비", "예비비", "생활용품", "교통/차량", "기타"])
    with c3: memo = st.text_input("내용")
    with c4: amt = st.number_input("금액(원)", min_value=0, step=1000)
    if st.button("추가하기"):
        if amt > 0:
            new_row = pd.DataFrame([{"date": pd.to_datetime(d), "category": cat, "memo": memo, "amount": int(amt)}])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.rerun()

# 데이터 집계
df = st.session_state.df.copy()
m_df = df[(df["date"].dt.year == YEAR) & (df["date"].dt.month == selected_month)]

# 카테고리별 지출액 계산
spent_food = int(m_df[m_df["category"] == "식비"]["amount"].sum())
spent_em = int(m_df[m_df["category"] == "예비비"]["amount"].sum())
spent_total = int(m_df["amount"].sum())

# 예산 잔액 계산
rem_food = food_budget - spent_food
rem_em = em_budget - spent_em

# 고정비 계산
current_fixed = [e for e in st.session_state.fixed_events if e.date.year == YEAR and e.date.month == selected_month]
f_total = sum(e.amount for e in current_fixed)
cur_income = st.session_state.income_data.get(f"{YEAR}-{selected_month:02d}", 0)
total_remaining = cur_income - f_total - spent_total

# -----------------------------
# 3. 상단 대시보드 (차감 표시)
# -----------------------------
st.markdown("### 📊 이번 달 예산 현황")
m1, m2, m3, m4 = st.columns(4)
m1.metric("월 수입", f"{cur_income:,.0f}원")
m2.metric("고정비 합계", f"{f_total:,.0f}원")
m3.metric("변동지출 합계", f"{spent_total:,.0f}원")
m4.metric("최종 잔액", f"{total_remaining:,.0f}원")

st.markdown("#### 🎯 카테고리별 남은 예산")
b1, b2 = st.columns(2)
# 잔액이 0보다 작으면 빨간색으로 경고 효과(delta 사용)
b1.metric("🍔 식비 잔액 (예산 대비)", f"{rem_food:,.0f}원", delta=f"지출: {spent_food:,.0f}", delta_color="inverse")
b2.metric("🚨 예비비 잔액 (예산 대비)", f"{rem_em:,.0f}원", delta=f"지출: {spent_em:,.0f}", delta_color="inverse")

# -----------------------------
# 4. 달력 및 상세 내역 (기존과 동일)
# -----------------------------
st.subheader("🗓️ 지출 달력")
# ... (달력 렌더링 코드 유지) ...
# (이전 답변의 달력 렌더링 코드를 그대로 사용하시면 됩니다.)

# 지출 내역 관리
st.markdown("---")
st.subheader("📜 상세 내역 및 삭제")
if not m_df.empty:
    st.dataframe(m_df.assign(date=m_df["date"].dt.date).sort_values("date"), use_container_width=True, hide_index=True)
    with st.expander("항목 삭제"):
        to_del = st.multiselect("삭제할 항목 선택", options=m_df.index, format_func=lambda x: f"{m_df.loc[x,'memo']} ({m_df.loc[x,'amount']:,}원)")
        if st.button("선택 삭제"):
            st.session_state.df = st.session_state.df.drop(to_del).reset_index(drop=True)
            st.rerun()
