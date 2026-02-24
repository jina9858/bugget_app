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
REF_DATE_FILE = "ref_dates.json"
CASH_ASSETS_FILE = "cash_assets.json"

# -----------------------------
# 1. 데이터 관리 로직
# -----------------------------
def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return default_val
    return default_val

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
    data = load_json(FIXED_FILE, [])
    if data:
        return [Event(date=dt.date.fromisoformat(r["date"]), category=r["category"], item=r["item"], amount=r["amount"], note=r.get("note","")) for r in data]
    base = build_fixed_events()
    save_json(FIXED_FILE, [{"date": e.date.isoformat(), "category": e.category, "item": e.item, "amount": e.amount, "note": e.note} for e in base])
    return base

def save_fixed_events(events: List[Event]):
    save_json(FIXED_FILE, [{"date": e.date.isoformat(), "category": e.category, "item": e.item, "amount": e.amount, "note": e.note} for e in events])

# -----------------------------
# 2. 세션 상태 관리
# -----------------------------
if "income_data" not in st.session_state: 
    st.session_state.income_data = load_json(INCOME_FILE, {f"{YEAR}-{m:02d}": 0 for m in range(START_MONTH, END_MONTH + 1)})
if "fixed_events" not in st.session_state: 
    st.session_state.fixed_events = load_fixed_events()
if "ref_dates" not in st.session_state:
    st.session_state.ref_dates = load_json(REF_DATE_FILE, {f"{YEAR}-{m:02d}": {"start": f"{YEAR}-{m:02d}-01", "end": f"{YEAR}-{m:02d}-24"} for m in range(START_MONTH, END_MONTH + 1)})
if "cash_data" not in st.session_state:
    st.session_state.cash_data = load_json(CASH_ASSETS_FILE, {"total_balance": 0, "monthly": {}})
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["date", "category", "memo", "amount"])
    st.session_state.df["date"] = pd.to_datetime(st.session_state.df["date"])

# ---------- Sidebar ----------
st.sidebar.header("⚙️ 예산 기간 설정")

selected_month = st.sidebar.selectbox("조회 월 선택", options=list(range(START_MONTH, END_MONTH + 1)), format_func=lambda m: f"{m}월")
month_key = f"{YEAR}-{selected_month:02d}"

# [핵심] 시작 날짜와 종료 날짜 선택 로직
saved_dates = st.session_state.ref_dates.get(month_key, {"start": f"{YEAR}-{selected_month:02d}-01", "end": f"{YEAR}-{selected_month:02d}-28"})
budget_start = st.sidebar.date_input(f"📅 {selected_month}월 예산 시작일", value=dt.date.fromisoformat(saved_dates["start"]))
budget_end = st.sidebar.date_input(f"🏁 {selected_month}월 예산 종료일", value=dt.date.fromisoformat(saved_dates["end"]))

# 날짜 변경 시 저장
if budget_start.isoformat() != saved_dates["start"] or budget_end.isoformat() != saved_dates["end"]:
    st.session_state.ref_dates[month_key] = {"start": budget_start.isoformat(), "end": budget_end.isoformat()}
    save_json(REF_DATE_FILE, st.session_state.ref_dates)
    st.rerun()

st.sidebar.markdown("---")
food_budget_total = st.sidebar.number_input("월 식비 총 예산", min_value=0, value=650000, step=10000)
em_budget_total = st.sidebar.number_input("월 예비비 총 예산", min_value=0, value=200000, step=10000)

# 🅿️ 현금 자산 관리
st.sidebar.markdown("---")
st.sidebar.markdown("### 🅿️ 현금 자산 (파킹) 관리")
cash_month_data = st.session_state.cash_data["monthly"].get(month_key, {"savings": 0, "withdrawal": 0, "withdrawal_date": budget_start.isoformat()})
monthly_savings = st.sidebar.number_input("이번 달 파킹(저금)", min_value=0, value=cash_month_data.get("savings", 0), step=10000)
withdrawal = st.sidebar.number_input("비상금 인출", min_value=0, value=cash_month_data.get("withdrawal", 0), step=10000)
withdrawal_date_val = cash_month_data.get("withdrawal_date", budget_start.isoformat())
withdrawal_date = st.sidebar.date_input("비상금 인출 날짜", value=dt.date.fromisoformat(withdrawal_date_val))

if st.sidebar.button("💰 자산 현황 업데이트"):
    old_data = st.session_state.cash_data["monthly"].get(month_key, {"savings": 0, "withdrawal": 0})
    diff = (monthly_savings - old_data.get("savings", 0)) - (withdrawal - old_data.get("withdrawal", 0))
    st.session_state.cash_data["total_balance"] += diff
    st.session_state.cash_data["monthly"][month_key] = {"savings": monthly_savings, "withdrawal": withdrawal, "withdrawal_date": withdrawal_date.isoformat()}
    save_json(CASH_ASSETS_FILE, st.session_state.cash_data)
    st.success("업데이트 완료!")
    st.rerun()

# 고정비/수입 편집
with st.sidebar.expander("📝 수입 및 고정비 항목 수정", expanded=False):
    income_df = pd.DataFrame([{"월": k, "수입(원)": v} for k, v in st.session_state.income_data.items()])
    edited_inc = st.data_editor(income_df, use_container_width=True, hide_index=True)
    fixed_df = pd.DataFrame([{"date": e.date.isoformat(), "item": e.item, "amount": e.amount, "category": e.category} for e in st.session_state.fixed_events])
    edited_fixed = st.data_editor(fixed_df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 모든 변경사항 저장"):
        st.session_state.income_data = dict(zip(edited_inc["월"], edited_inc["수입(원)"]))
        save_json(INCOME_FILE, st.session_state.income_data)
        new_fixed = [Event(date=dt.date.fromisoformat(r["date"]), category=r["category"], item=r["item"], amount=r["amount"]) for r in edited_fixed.to_dict(orient="records")]
        st.session_state.fixed_events = new_fixed
        save_fixed_events(new_fixed)
        st.rerun()

# ---------- Main ----------
st.title(f"📅 {YEAR}년 {selected_month}월 예산 달력")

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
# 3. 데이터 집계 및 [기간 기반 계산]
# -----------------------------
df = st.session_state.df.copy()
monthly_carry_over = 0
for m in range(START_MONTH, selected_month):
    m_inc = st.session_state.income_data.get(f"{YEAR}-{m:02d}", 0)
    m_fixed = sum(e.amount for e in st.session_state.fixed_events if e.date.year == YEAR and e.date.month == m)
    m_var = int(df[(df["date"].dt.year == YEAR) & (df["date"].dt.month == m)]["amount"].sum())
    monthly_carry_over += (m_inc - m_fixed - m_var)

# 이번 달 데이터
m_df_full = df[(df["date"].dt.year == YEAR) & (df["date"].dt.month == selected_month)]
cur_inc = st.session_state.income_data.get(month_key, 0)

# [수정] 설정한 기간(budget_start ~ budget_end) 사이의 내역만 합산
f_period_total = sum(e.amount for e in st.session_state.fixed_events if budget_start <= e.date <= budget_end)
v_period_total = int(m_df_full[(m_df_full["date"].dt.date >= budget_start) & (m_df_full["date"].dt.date <= budget_end)]["amount"].sum())

# 가용 잔액 계산
total_balance = cur_inc - monthly_savings - f_period_total - v_period_total + monthly_carry_over + withdrawal

# 주간 식비 계산 (달력의 주차 기준, 단 기간 내 지출만 반영)
cal_obj = calendar.Calendar(firstweekday=0)
weeks_list = cal_obj.monthdayscalendar(YEAR, selected_month)
weekly_food_base = food_budget_total / len(weeks_list)
weekly_food_balances = {}; food_carry = 0
for week in weeks_list:
    v_days = [d for d in week if d > 0]
    if not v_days: continue
    # 기간 내의 지출만 주차별로 합산
    w_spent = int(m_df_full[(m_df_full["category"] == "식비") & (m_df_full["date"].dt.day >= v_days[0]) & (m_df_full["date"].dt.day <= v_days[-1]) & (m_df_full["date"].dt.date >= budget_start) & (m_df_full["date"].dt.date <= budget_end)]["amount"].sum())
    w_available = weekly_food_base + food_carry
    w_balance = w_available - w_spent
    sun_day = week[6]
    if sun_day > 0: weekly_food_balances[sun_day] = w_balance
    else: weekly_food_balances[v_days[-1]] = w_balance
    food_carry = w_balance

rem_em_in_period = em_budget_total - int(m_df_full[(m_df_full["category"] == "예비비") & (m_df_full["date"].dt.date >= budget_start) & (m_df_full["date"].dt.date <= budget_end)]["amount"].sum())

# -----------------------------
# 4. 상단 대시보드
# -----------------------------
st.markdown(f"### 📊 예산 기간: {budget_start.strftime('%m/%d')} ~ {budget_end.strftime('%m/%d')}")
if withdrawal > 0:
    st.error(f"🚨 비상금 인출 발생!! {withdrawal_date.strftime('%m/%d')}에 파킹 자산에서 {withdrawal:,.0f}원을 인출하여 합산되었습니다.")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("월 수입", f"{cur_inc:,.0f}원")
m2.metric("기간 고정비", f"{f_period_total:,.0f}원")
m3.metric("기간 변동지출", f"{v_period_total:,.0f}원")
m4.metric("💰 총 현금 자산", f"{st.session_state.cash_data['total_balance']:,.0f}원")
m5.metric("현재 가용 잔액", f"{total_balance:,.0f}원")

# -----------------------------
# 5. 지출 달력
# -----------------------------
st.markdown("---")
st.subheader("🗓️ 지출 달력")
f_date_map = {}; s_date_map = {}
for e in [x for x in st.session_state.fixed_events if x.date.year == YEAR and x.date.month == selected_month]:
    f_date_map.setdefault(e.date.day, []).append(e)
for _, r in m_df_full.iterrows():
    s_date_map.setdefault(int(r["date"].day), []).append((r["category"], r["amount"], r["memo"]))

cols = st.columns(7)
for idx, name in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
    cols[idx].markdown(f"<div style='text-align:center; background:#eee; padding:5px; border-radius:5px;'><b>{name}</b></div>", unsafe_allow_html=True)

for week in weeks_list:
    cols = st.columns(7)
    for idx, day_num in enumerate(week):
        if day_num == 0:
            cols[idx].markdown("<div style='height:200px; background:#f9f9f9; border:1px solid #eee; border-radius:8px;'></div>", unsafe_allow_html=True)
            continue
        
        # [수정] 선택한 기간 내에 있는지 확인
        current_date = dt.date(YEAR, selected_month, day_num)
        is_in_period = (budget_start <= current_date <= budget_end)
        
        cell_html = [f"<div style='font-weight:bold; color:{'#2ecc71' if is_in_period else '#999'};'>{day_num}</div>"]
        
        if is_in_period:
            # 기간 내에 있을 때만 정보 표시
            if idx == 6:
                header_parts = []
                if day_num in weekly_food_balances: header_parts.append(f"🍞 식비: {weekly_food_balances[day_num]:,.0f}")
                header_parts.append(f"🚨 예비: {rem_em_in_period:,.0f}")
                cell_html.append(f"<div style='margin-bottom:10px; padding:3px; background:#f1f9f4; border-radius:4px; font-size:10px; color:#27ae60; font-weight:bold; text-align:center;'>{' | '.join(header_parts)}</div>")

            # 비상금 인출 표시
            w_info = st.session_state.cash_data["monthly"].get(month_key, {})
            if w_info.get("withdrawal", 0) > 0:
                w_d = dt.date.fromisoformat(w_info.get("withdrawal_date"))
                if w_d == current_date:
                    cell_html.append(f"<div style='background-color:#ff4b4b; color:white; padding:5px; border-radius:5px; font-weight:bold; text-align:center; font-size:11px; margin-bottom:8px;'>💸 비상금 인출: {w_info['withdrawal']:,.0f}원</div>")

            # 고정비/변동비 표시
            day_fixed = f_date_map.get(day_num, [])
            day_spent = s_date_map.get(day_num, [])
            if day_fixed:
                cell_html.append(f"<div style='color:#e74c3c; font-size:11px; font-weight:bold;'>고정: {sum(e.amount for e in day_fixed):,.0f}</div>")
                for e in day_fixed: cell_html.append(f"<div style='color:#c0392b; font-size:10px;'>· {e.item} ({e.amount:,.0f})</div>")
            if day_spent:
                cell_html.append(f"<div style='color:#3498db; font-size:11px; font-weight:bold; margin-top:5px;'>변동: {sum(a for _, a, _ in day_spent):,.0f}</div>")
                for c, a, m in day_spent:
                    txt = m if m else c
                    cell_html.append(f"<div style='color:#2980b9; font-size:10px;'>· {txt} ({a:,.0f})</div>")
        
        bg_color = "#ffffff" if not is_in_period else ("#fff4f4" if f_date_map.get(day_num, []) else "#ffffff")
        period_style = "border: 2px solid #2ecc71;" if is_in_period else "border: 1px solid #eee;"
        cols[idx].markdown(f"<div style='height:200px; {period_style} padding:8px; background:{bg_color}; border-radius:8px; overflow-y:auto;'>{''.join(cell_html)}</div>", unsafe_allow_html=True)

# 상세 내역
st.markdown("---")
st.subheader("📜 이번 달 상세 지출 내역")
if not m_df_full.empty:
    st.data_editor(m_df_full.assign(date=m_df_full["date"].dt.date).sort_values("date"), use_container_width=True, hide_index=True)
