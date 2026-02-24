import streamlit as st
import pandas as pd
import calendar
import datetime as dt
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple

# 0. 페이지 기본 설정
st.set_page_config(page_title="예산 달력", layout="wide")

# --- 전역 설정값 ---
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
st.sidebar.header("⚙️ 기준 설정")
simulated_today = st.sidebar.date_input("🗓️ 기준 날짜 설정 (오늘)", value=dt.date(2026, 2, 24))
selected_month = st.sidebar.selectbox("조회 월 선택", options=list(range(START_MONTH, END_MONTH + 1)), format_func=lambda m: f"{m}월")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🍔 식비/🚨 예비비 예산")
food_budget_total = st.sidebar.number_input("월 식비 총 예산", min_value=0, value=650000, step=10000)
em_budget_total = st.sidebar.number_input("월 예비비 총 예산", min_value=0, value=200000, step=10000)

with st.sidebar.expander("📝 수입/고정비 수정"):
    income_df = pd.DataFrame([{"월": k, "수입(원)": v} for k, v in st.session_state.income_data.items()])
    edited_inc = st.data_editor(income_df, use_container_width=True, hide_index=True)
    if st.button("수입 저장"):
        st.session_state.income_data = dict(zip(edited_inc["월"], edited_inc["수입(원)"]))
        save_income(st.session_state.income_data)
        st.rerun()

# ---------- Main ----------
st.title(f"📅 {YEAR}년 {selected_month}월 예산 달력")

# [과거 달력 숨김 로직]
if simulated_today.year == YEAR and selected_month < simulated_today.month:
    st.warning(f"선택하신 {selected_month}월은 이미 지난 달입니다. 기준 날짜({simulated_today.month}월) 이후의 달력만 조회 가능합니다.")
    st.stop()

# 지출 입력
with st.expander("➕ 지출 추가하기", expanded=True):
    c1, c2, c3, c4 = st.columns([1.2, 1.0, 2.0, 1.0])
    with c1: d = st.date_input("날짜", value=dt.date(YEAR, selected_month, 1))
    with c2: cat = st.selectbox("분류", ["식비", "예비비", "생활용품", "교통/차량", "기타"])
    with c3: memo = st.text_input("내용")
    with c4: amt = st.number_input("금액(원)", min_value=0, step=1000)
    if st.button("지출 추가"):
        if amt > 0:
            new_row = pd.DataFrame([{"date": pd.to_datetime(d), "category": cat, "memo": memo, "amount": int(amt)}])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.rerun()

# -----------------------------
# 3. 데이터 집계 및 계산
# -----------------------------
df = st.session_state.df.copy()

# 월간 이월금 계산
monthly_carry_over = 0
for m in range(START_MONTH, selected_month):
    m_inc = st.session_state.income_data.get(f"{YEAR}-{m:02d}", 0)
    m_fixed = sum(e.amount for e in st.session_state.fixed_events if e.date.year == YEAR and e.date.month == m)
    m_var = int(df[(df["date"].dt.year == YEAR) & (df["date"].dt.month == m)]["amount"].sum())
    monthly_carry_over += (m_inc - m_fixed - m_var)

m_df = df[(df["date"].dt.year == YEAR) & (df["date"].dt.month == selected_month)]
cur_inc = st.session_state.income_data.get(f"{YEAR}-{selected_month:02d}", 0)
cur_fixed_list = [e for e in st.session_state.fixed_events if e.date.year == YEAR and e.date.month == selected_month]
f_total = sum(e.amount for e in cur_fixed_list)
v_total = int(m_df["amount"].sum())
total_balance = cur_inc - f_total - v_total + monthly_carry_over

# [주간 식비 계산 로직 - 실제 달력 주차 기준]
cal_obj = calendar.Calendar(firstweekday=0)
weeks_list = cal_obj.monthdayscalendar(YEAR, selected_month)
num_weeks = len(weeks_list)
weekly_food_base = food_budget_total / num_weeks

weekly_food_balances = {}
food_carry = 0
for week in weeks_list:
    valid_days = [d for d in week if d > 0]
    if not valid_days: continue
    w_start, w_end = valid_days[0], valid_days[-1]
    w_spent = int(m_df[(m_df["category"] == "식비") & (m_df["date"].dt.day >= w_start) & (m_df["date"].dt.day <= w_end)]["amount"].sum())
    w_available = weekly_food_base + food_carry
    w_balance = w_available - w_spent
    
    # 일요일(마지막 열)에 잔액 저장
    sunday_day = week[6]
    if sunday_day > 0: weekly_food_balances[sunday_day] = w_balance
    else: weekly_food_balances[w_end] = w_balance
    food_carry = w_balance

# 예비비 잔액 계산
spent_em_total = int(m_df[m_df["category"] == "예비비"]["amount"].sum())
rem_em_monthly = em_budget_total - spent_em_total

# -----------------------------
# 4. 상단 대시보드
# -----------------------------
st.markdown("### 📊 종합 예산 현황")
st.caption(f"📍 현재 기준 날짜: {simulated_today.strftime('%Y-%m-%d')}")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("월 수입", f"{cur_inc:,.0f}원")
m2.metric("고정비", f"{f_total:,.0f}원")
m3.metric("변동지출", f"{v_total:,.0f}원")
m4.metric("지난달 이월", f"{monthly_carry_over:,.0f}원", delta=monthly_carry_over)
m5.metric("최종 잔액", f"{total_balance:,.0f}원")

# -----------------------------
# 5. 지출 달력
# -----------------------------
st.markdown("---")
st.subheader("🗓️ 지출 달력")
st.caption("💡 **식비 잔액**은 일요일에만 표시되며, **예비비 잔액**은 매일 하단에 표시됩니다.")

f_date_map = {}; s_date_map = {}
for e in cur_fixed_list: f_date_map.setdefault(e.date.day, []).append(e)
for _, r in m_df.iterrows(): s_date_map.setdefault(int(r["date"].day), []).append((r["category"], r["amount"], r["memo"]))

cols = st.columns(7)
for idx, name in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
    cols[idx].markdown(f"<div style='text-align:center; background:#eee; padding:5px; border-radius:5px;'><b>{name}</b></div>", unsafe_allow_html=True)

for week in weeks_list:
    cols = st.columns(7)
    for idx, day_num in enumerate(week):
        if day_num == 0:
            cols[idx].markdown("<div style='height:200px; background:#f9f9f9; border:1px solid #eee; border-radius:8px;'></div>", unsafe_allow_html=True)
            continue
        
        day_fixed = f_date_map.get(day_num, [])
        day_spent = s_date_map.get(day_num, [])
        sum_fixed = sum(e.amount for e in day_fixed)
        sum_spent = sum(a for _, a, _ in day_spent)
        
        is_today = (day_num == simulated_today.day and selected_month == simulated_today.month)
        today_style = "border: 2px solid #2ecc71;" if is_today else "border: 1px solid #ddd;"
        
        cell_html = [f"<div style='font-weight:bold; color:{'#2ecc71' if is_today else '#333'};'>{day_num}</div>"]
        
        if day_fixed:
            cell_html.append(f"<div style='color:#e74c3c; font-size:11px; font-weight:bold;'>고정: {sum_fixed:,.0f}</div>")
            for e in day_fixed: cell_html.append(f"<div style='color:#c0392b; font-size:10px;'>· {e.item}</div>")
        if day_spent:
            cell_html.append(f"<div style='color:#3498db; font-size:11px; font-weight:bold; margin-top:5px;'>변동: {sum_spent:,.0f}</div>")
            for c, a, m in day_spent:
                txt = m if m else c
                cell_html.append(f"<div style='color:#2980b9; font-size:10px;'>· {txt} ({a:,.0f})</div>")
        
        footer_html = []
        if idx == 6 and day_num in weekly_food_balances:
            w_bal = weekly_food_balances[day_num]
            footer_html.append(f"<div style='margin-top:10px; padding:3px; background:#f1f9f4; border-radius:4px; font-size:11px; color:#27ae60; font-weight:bold; text-align:center;'>🍞 식비잔액: {w_bal:,.0f}</div>")
        footer_html.append(f"<div style='margin-top:5px; font-size:10px; color:#7f8c8d; text-align:right;'>🚨 예비비: {rem_em_monthly:,.0f}</div>")
        
        cell_html.append("".join(footer_html))
        bg_color = "#ffffff" if not day_fixed else "#fff4f4"
        cols[idx].markdown(f"<div style='height:200px; {today_style} padding:8px; background:{bg_color}; border-radius:8px; overflow-y:auto;'>{''.join(cell_html)}</div>", unsafe_allow_html=True)

# -----------------------------
# 6. 상세 지출 내역 관리 (복구 완료!)
# -----------------------------
st.markdown("---")
st.subheader("📜 이번 달 상세 지출 내역")
if not m_df.empty:
    # 1. 수정 기능: data_editor를 사용하여 표에서 직접 수정 가능
    st.info("💡 아래 표에서 내용을 직접 클릭하여 수정할 수 있습니다.")
    edited_m_df = st.data_editor(
        m_df.assign(date=m_df["date"].dt.date).sort_values("date"),
        use_container_width=True,
        hide_index=True,
        key="main_expense_editor"
    )
    
    # 2. 삭제 기능: 멀티셀렉트와 버튼 사용
    with st.expander("🗑️ 지출 항목 삭제", expanded=False):
        to_del = st.multiselect(
            "삭제할 항목을 선택하세요 (여러 개 선택 가능)", 
            options=list(m_df.index), 
            format_func=lambda x: f"{m_df.loc[x,'date'].date()} | {m_df.loc[x,'memo']} | {m_df.loc[x,'amount']:,}원"
        )
        if st.button("선택한 항목 삭제"):
            st.session_state.df = st.session_state.df.drop(to_del).reset_index(drop=True)
            st.success("성공적으로 삭제되었습니다!")
            st.rerun()
else:
    st.info("이번 달에 입력된 지출 내역이 없습니다.")
