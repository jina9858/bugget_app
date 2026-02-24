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
# 1. 데이터 관리 로직
# -----------------------------
def load_income() -> Dict[str, int]:
    default_income = {f"{YEAR}-{m:02d}": 0 for m in range(START_MONTH, END_MONTH + 1)}
    default_income[f"{YEAR}-02"] = 4400000
    default_income[f"{YEAR}-03"] = 5650000
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

def last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]

def next_monday_if_weekend(d: dt.date) -> dt.date:
    if d.weekday() == 5: return d + dt.timedelta(days=2)
    if d.weekday() == 6: return d + dt.timedelta(days=1)
    return d

def build_fixed_events(year=YEAR, start_month=START_MONTH, end_month=END_MONTH) -> List[Event]:
    events: List[Event] = []
    feb_cutoff = dt.date(YEAR, 2, 22)
    for m in range(start_month, end_month + 1):
        events += [
            Event(dt.date(year, m, 5),  "생활/구독", "금천누리복지 후원", 50000),
            Event(dt.date(year, m, 9),  "통신",     "LGU+ 휴대폰",      19220),
            Event(dt.date(year, m, 10), "공과금",   "도시가스",         70913),
            Event(dt.date(year, m, 10), "수수료",   "SMS 수수료",          300),
            Event(dt.date(year, m, 12), "공과금",   "수도요금",         28370),
            Event(dt.date(year, m, 23), "계돈/송금", "계돈(김아름)",     100000),
            Event(dt.date(year, m, 23), "계돈/송금", "정기송금(김주환)", 100000),
            Event(dt.date(year, m, 23), "계돈/송금", "계돈(우연지)",      30000),
            Event(dt.date(year, m, 23), "계돈/송금", "계돈(김영민)",      20000),
            Event(dt.date(year, m, 25), "금융/보험", "교보생명",         212108),
            Event(dt.date(year, m, 25), "금융/보험", "농협생명",         136200),
            Event(dt.date(year, m, 25), "공과금",   "전기요금",          26166),
            Event(dt.date(year, m, 25), "보험",     "카카오페이 운전자보험", 8800),
            Event(dt.date(year, m, 26), "통신",     "LGU+ 인터넷",       32830),
        ]
        for dday in [5, 10, 15, 20, 25, 30]:
            if dday <= last_day(year, m):
                events.append(Event(dt.date(year, m, dday), "보험", "메리츠 운전자보험", 10280))
        if m >= 3:
            events.append(Event(dt.date(year, m, 13), "생활/구독", "네이버 멤버십", 4900))
            events.append(Event(dt.date(year, m, 24), "생활/구독", "AI 구독",      30000))
        ld = dt.date(year, m, last_day(year, m))
        events.append(Event(next_monday_if_weekend(ld), "주거/공과금", "관리비", 110000))
    return [e for e in events if not (e.date.year == YEAR and e.date.month == 2 and e.date < feb_cutoff)]

def load_fixed_events() -> List[Event]:
    if os.path.exists(FIXED_FILE):
        try:
            with open(FIXED_FILE, "r", encoding="utf-8") as f:
                return [Event(date=dt.date.fromisoformat(r["date"]), category=r["category"], item=r["item"], amount=r["amount"], note=r.get("note","")) for r in json.load(f)]
        except: pass
    base = build_fixed_events()
    save_fixed_events(base)
    return base

def save_fixed_events(events: List[Event]):
    with open(FIXED_FILE, "w", encoding="utf-8") as f:
        json.dump([{"date": e.date.isoformat(), "category": e.category, "item": e.item, "amount": e.amount, "note": e.note} for e in events], f, ensure_ascii=False, indent=2)

# -----------------------------
# 2. 세션 상태 관리
# -----------------------------
if "income_data" not in st.session_state: st.session_state.income_data = load_income()
if "fixed_events" not in st.session_state: st.session_state.fixed_events = load_fixed_events()
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["date", "category", "memo", "amount"])
    st.session_state.df["date"] = pd.to_datetime(st.session_state.df["date"])

# ---------- Sidebar ----------
st.sidebar.header("⚙️ 예산 설정")
selected_month = st.sidebar.selectbox("조회 월 선택", options=list(range(START_MONTH, END_MONTH + 1)), format_func=lambda m: f"{m}월")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🍔 식비/🚨 예비비 예산")
food_budget = st.sidebar.number_input("월 식비 총 예산", min_value=0, value=650000, step=10000)
em_budget = st.sidebar.number_input("월 예비비 총 예산", min_value=0, value=200000, step=10000)

with st.sidebar.expander("📝 수입/고정비 수정"):
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

# -----------------------------
# 3. 주 단위 식비 이월 로직 계산
# -----------------------------
df = st.session_state.df.copy()
m_df = df[(df["date"].dt.year == YEAR) & (df["date"].dt.month == selected_month)]

total_days = last_day(YEAR, selected_month)
# 주차 정의 (7일 단위)
week_ranges = [(1, 7), (8, 14), (15, 21), (22, total_days)]
weekly_food_budget = food_budget / len(week_ranges) # 단순하게 주차수로 나눔

weekly_data = []
carry_over = 0
today_day = dt.date.today().day if dt.date.today().month == selected_month else 0

current_week_info = None

for i, (start, end) in enumerate(week_ranges):
    # 해당 주차 식비 지출 계산
    week_spent = int(m_df[(m_df["category"] == "식비") & (m_df["date"].dt.day >= start) & (m_df["date"].dt.day <= end)]["amount"].sum())
    
    # 이번 주 가용 금액 = 주간 예산 + 이전 주 이월금
    available = weekly_food_budget + carry_over
    balance = available - week_spent
    
    weekly_data.append({
        "주차": f"{i+1}주 ({start}일~{end}일)",
        "예산": weekly_food_budget,
        "이월금": carry_over,
        "지출": week_spent,
        "잔액": balance
    })
    
    # 현재 날짜가 포함된 주차 정보 저장
    if start <= today_day <= end:
        current_week_info = weekly_data[-1]
    
    # 다음 주차로 이월 (남으면 +, 모자라면 -)
    carry_over = balance

# -----------------------------
# 4. 상단 대시보드
# -----------------------------
cur_inc = st.session_state.income_data.get(f"{YEAR}-{selected_month:02d}", 0)
cur_fixed = [e for e in st.session_state.fixed_events if e.date.year == YEAR and e.date.month == selected_month]
f_total = sum(e.amount for e in cur_fixed)
v_total = int(m_df["amount"].sum())
total_rem = cur_inc - f_total - v_total

st.markdown("### 📊 이번 달 종합 현황")
m1, m2, m3, m4 = st.columns(4)
m1.metric("월 수입", f"{cur_inc:,.0f}원")
m2.metric("고정비", f"{f_total:,.0f}원")
m3.metric("변동지출", f"{v_total:,.0f}원")
m4.metric("최종 잔액", f"{total_rem:,.0f}원")

st.markdown("---")
st.markdown("### 🍞 식비 주간 이월 관리")
if current_week_info:
    c1, c2, c3 = st.columns(3)
    c1.metric("이번 주 사용 가능", f"{current_week_info['예산'] + current_week_info['이월금']:,.0f}원", help="주간 예산 + 지난주 이월금")
    c2.metric("이번 주 지출", f"{current_week_info['지출']:,.0f}원")
    c3.metric("이번 주 남은 금액", f"{current_week_info['잔액']:,.0f}원", delta=current_week_info['잔액'], delta_color="normal")

with st.expander("📅 주차별 식비 상세 내역 보기"):
    st.table(pd.DataFrame(weekly_data).style.format({"예산": "{:,.0f}", "이월금": "{:,.0f}", "지출": "{:,.0f}", "잔액": "{:,.0f}"}))

# -----------------------------
# 5. 달력 출력 (기존 유지)
# -----------------------------
st.markdown("---")
st.subheader("🗓️ 지출 달력")
cal = calendar.Calendar(firstweekday=0)
weeks = cal.monthdayscalendar(YEAR, selected_month)

f_map = {}; s_map = {}
for e in cur_fixed: f_map.setdefault(e.date.day, []).append(e)
for _, r in m_df.iterrows(): s_map.setdefault(int(r["date"].day), []).append((r["category"], r["amount"], r["memo"]))

cols = st.columns(7)
for i, d_name in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
    cols[i].markdown(f"<div style='text-align:center;'><b>{d_name}</b></div>", unsafe_allow_html=True)

for week in weeks:
    cols = st.columns(7)
    for i, daynum in enumerate(week):
        if daynum == 0:
            cols[i].markdown("<div style='height:160px; background:#f0f2f6; border-radius:8px;'></div>", unsafe_allow_html=True)
            continue
        
        f_list = f_map.get(daynum, []); s_list = s_map.get(daynum, [])
        f_sum = sum(e.amount for e in f_list); s_sum = sum(a for _, a, _ in s_list)
        content = [f"<div style='font-weight:bold; border-bottom:1px solid #eee; margin-bottom:5px;'>{daynum}</div>"]
        if f_list:
            content.append(f"<div style='color:#e74c3c; font-size:11px; font-weight:bold;'>고정: {f_sum:,.0f}</div>")
            for e in f_list: content.append(f"<div style='color:#c0392b; font-size:10px;'>· {e.item} ({e.amount:,.0f})</div>")
        if s_list:
            content.append(f"<div style='color:#3498db; font-size:11px; font-weight:bold; margin-top:5px;'>변동: {s_sum:,.0f}</div>")
            for cat, amt, memo in s_list:
                display = memo if memo else cat
                content.append(f"<div style='color:#2980b9; font-size:10px;'>· {display} ({amt:,.0f})</div>")
        
        bg = "#ffffff" if not f_list else "#fff4f4"
        cols[i].markdown(f"<div style='height:160px; border:1px solid #ddd; padding:8px; background:{bg}; border-radius:8px; overflow-y:auto;'>{''.join(content)}</div>", unsafe_allow_html=True)

# 상세 내역
st.markdown("---")
st.subheader("📜 상세 지출 내역")
if not m_df.empty:
    st.dataframe(m_df.assign(date=m_df["date"].dt.date).sort_values("date"), use_container_width=True, hide_index=True)
