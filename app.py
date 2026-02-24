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
            try: events.append(Event(dt.date(year, m, dday), "보험", "메리츠 운전자보험", 10280))
            except: pass
        if m >= 3:
            events.append(Event(dt.date(year, m, 13), "생활/구독", "네이버 멤버십", 4900))
            events.append(Event(dt.date(year, m, 24), "생활/구독", "AI 구독",      30000))
        try:
            ld_val = calendar.monthrange(year, m)[1]
            events.append(Event(next_monday_if_weekend(dt.date(year, m, ld_val)), "주거/공과금", "관리비", 110000))
        except: pass
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
# 2. 세션 상태 및 실제 오늘 날짜 (2026-02-24)
# -----------------------------
actual_today = dt.date(2026, 2, 24)

if "income_data" not in st.session_state: 
    st.session_state.income_data = load_json(INCOME_FILE, {f"{YEAR}-{m:02d}": 0 for m in range(START_MONTH, END_MONTH + 1)})
if "fixed_events" not in st.session_state: 
    st.session_state.fixed_events = load_fixed_events()
if "ref_dates" not in st.session_state:
    st.session_state.ref_dates = load_json(REF_DATE_FILE, {})
if "cash_data" not in st.session_state:
    st.session_state.cash_data = load_json(CASH_ASSETS_FILE, {"total_balance": 0, "monthly": {}})
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["date", "category", "memo", "amount"])
    st.session_state.df["date"] = pd.to_datetime(st.session_state.df["date"])

# ---------- Sidebar ----------
st.sidebar.header("⚙️ 예산 설정")
st.sidebar.info(f"✨ 실제 오늘: {actual_today.strftime('%Y-%m-%d')}")

selected_month = st.sidebar.selectbox("조회 월 선택", options=list(range(START_MONTH, END_MONTH + 1)), format_func=lambda m: f"{m}월")
month_key = f"{YEAR}-{selected_month:02d}"

saved_val = st.session_state.ref_dates.get(month_key)
if isinstance(saved_val, dict) and "start" in saved_val: saved_dates = saved_val
else: saved_dates = {"start": f"{YEAR}-{selected_month:02d}-01", "end": f"{YEAR}-{selected_month:02d}-24"}

budget_start = st.sidebar.date_input(f"📅 예산 시작일", value=dt.date.fromisoformat(saved_dates["start"]))
budget_end = st.sidebar.date_input(f"🏁 예산 종료일", value=dt.date.fromisoformat(saved_dates["end"]))

if budget_start.isoformat() != saved_dates.get("start") or budget_end.isoformat() != saved_dates.get("end"):
    st.session_state.ref_dates[month_key] = {"start": budget_start.isoformat(), "end": budget_end.isoformat()}
    save_json(REF_DATE_FILE, st.session_state.ref_dates)
    st.rerun()

st.sidebar.markdown("---")
food_budget_total = st.sidebar.number_input("🍔 월 식비 총 예산", min_value=0, value=650000, step=10000)
household_budget_total = st.sidebar.number_input("🧺 월 생활용품 예산", min_value=0, value=100000, step=10000)
transport_budget_total = st.sidebar.number_input("🚗 월 차량/교통 예산", min_value=0, value=150000, step=10000)
em_budget_total = st.sidebar.number_input("🚨 월 예비비 예산", min_value=0, value=200000, step=10000)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🅿️ 현금 자산 (파킹) 관리")
cash_month_data = st.session_state.cash_data["monthly"].get(month_key, {"savings": 0, "withdrawal": 0, "withdrawal_date": budget_start.isoformat()})
monthly_savings = st.sidebar.number_input("이번 달 파킹(저금)", min_value=0, value=cash_month_data.get("savings", 0), step=10000)
withdrawal = st.sidebar.number_input("비상금 인출", min_value=0, value=cash_month_data.get("withdrawal", 0), step=10000)
withdrawal_date_val = cash_month_data.get("withdrawal_date", budget_start.isoformat())
try: withdrawal_date = st.sidebar.date_input("비상금 인출 날짜", value=dt.date.fromisoformat(withdrawal_date_val))
except: withdrawal_date = st.sidebar.date_input("비상금 인출 날짜", value=budget_start)

if st.sidebar.button("💰 자산 현황 업데이트"):
    old_data = st.session_state.cash_data["monthly"].get(month_key, {"savings": 0, "withdrawal": 0})
    diff = (monthly_savings - old_data.get("savings", 0)) - (withdrawal - old_data.get("withdrawal", 0))
    st.session_state.cash_data["total_balance"] += diff
    st.session_state.cash_data["monthly"][month_key] = {"savings": monthly_savings, "withdrawal": withdrawal, "withdrawal_date": withdrawal_date.isoformat()}
    save_json(CASH_ASSETS_FILE, st.session_state.cash_data)
    st.rerun()

with st.sidebar.expander("📝 수입 및 고정비 항목 수정"):
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
st.title(f"📅 {selected_month}월 예산 달력")

with st.expander("➕ 지출 추가하기", expanded=True):
    c1, c2, c3, c4 = st.columns([1.2, 1.0, 2.0, 1.0])
    with c1: d = st.date_input("날짜", value=budget_start)
    with c2: cat = st.selectbox("분류", ["식비", "생활용품", "교통/차량", "예비비", "기타"])
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
monthly_carry_over = 0
for m in range(START_MONTH, selected_month):
    m_inc = st.session_state.income_data.get(f"{YEAR}-{m:02d}", 0)
    m_fixed = sum(e.amount for e in st.session_state.fixed_events if e.date.year == YEAR and e.date.month == m)
    m_var = int(df[(df["date"].dt.year == YEAR) & (df["date"].dt.month == m)]["amount"].sum())
    monthly_carry_over += (m_inc - m_fixed - m_var)

cur_inc = st.session_state.income_data.get(month_key, 0)
period_fixed_events = [e for e in st.session_state.fixed_events if budget_start <= e.date <= budget_end]
paid_fixed_sum = sum(e.amount for e in period_fixed_events if e.date <= actual_today)
rem_fixed_sum = sum(e.amount for e in period_fixed_events if e.date > actual_today)
v_period_df = df[(df["date"].dt.date >= budget_start) & (df["date"].dt.date <= budget_end)]
total_balance = cur_inc - monthly_savings - (paid_fixed_sum + rem_fixed_sum) - int(v_period_df["amount"].sum()) + monthly_carry_over + withdrawal

# 달력 그리드 생성
date_list = []
curr = budget_start
while curr <= budget_end:
    date_list.append(curr)
    curr += dt.timedelta(days=1)

start_weekday = budget_start.weekday()
full_grid = [None] * start_weekday + date_list
padding = (7 - (len(full_grid) % 7)) % 7
full_grid += [None] * padding
weeks = [full_grid[i:i+7] for i in range(0, len(full_grid), 7)]

# [수정] 식비 및 기타 예산 잔액 계산 (이월 없음)
weekly_food_base = food_budget_total / len(weeks)
weekly_food_balances = {}
total_food_surplus_deficit = 0

for week_row in weeks:
    valid = [d for d in week_row if d is not None]
    if not valid: continue
    ws, we = valid[0], valid[-1]
    
    # 해당 주차 식비 지출 및 잔액 (독립적 관리)
    w_food_spent = int(v_period_df[(v_period_df["category"] == "식비") & (v_period_df["date"].dt.date >= ws) & (v_period_df["date"].dt.date <= we)]["amount"].sum())
    w_food_bal = weekly_food_base - w_food_spent
    total_food_surplus_deficit += w_food_bal # 대시보드 표시용 합산
    
    # 주차별 누적 지출 (기타 항목은 월 단위)
    cum_spent_df = v_period_df[v_period_df["date"].dt.date <= we]
    rem_hh = household_budget_total - int(cum_spent_df[cum_spent_df["category"] == "생활용품"]["amount"].sum())
    rem_tr = transport_budget_total - int(cum_spent_df[cum_spent_df["category"] == "교통/차량"]["amount"].sum())
    rem_em = em_budget_total - int(cum_spent_df[cum_spent_df["category"] == "예비비"]["amount"].sum())
    
    target_date = week_row[6] if (len(week_row) > 6 and week_row[6]) else we
    weekly_food_balances[target_date] = {
        "food": w_food_bal,
        "household": rem_hh,
        "transport": rem_tr,
        "reserve": rem_em
    }

# -----------------------------
# 4. 상단 대시보드 (강화된 예산 현황 라인 추가)
# -----------------------------
st.markdown(f"### 📊 자금 흐름 현황 (기간: {budget_start.strftime('%m/%d')} ~ {budget_end.strftime('%m/%d')})")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("월 수입", f"{cur_inc:,.0f}원")
m2.metric("✅ 나간 고정비", f"{paid_fixed_sum:,.0f}원")
m3.metric("⏳ 남은 고정비", f"{rem_fixed_sum:,.0f}원")
m4.metric("💰 총 현금 자산", f"{st.session_state.cash_data['total_balance']:,.0f}원")
m5.metric("현재 가용 잔액", f"{total_balance:,.0f}원")

# [추가] 예산 상세 현황 라인 (크게 표시)
st.markdown("---")
st.markdown("### 🎯 주간/월간 예산 상세 현황")
b1, b2, b3, b4, b5 = st.columns(5)
b1.metric("🍔 식비 총 예산", f"{food_budget_total:,.0f}원")
b2.metric("🧺 생활용품", f"{household_budget_total:,.0f}원")
b3.metric("🚗 차량/교통", f"{transport_budget_total:,.0f}원")
b4.metric("🚨 예비비", f"{em_budget_total:,.0f}원")
# 누적 식비 절약/초과분 표시
food_delta_label = "절약됨" if total_food_surplus_deficit >= 0 else "초과됨"
b5.metric(f"🥗 식비 총 정산 ({food_delta_label})", f"{total_food_surplus_deficit:,.0f}원", delta=total_food_surplus_deficit)

# -----------------------------
# 5. 지출 달력
# -----------------------------
st.markdown("---")
st.subheader("🗓️ 지출 달력")
header_cols = st.columns(7)
for idx, name in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
    header_cols[idx].markdown(f"<div style='text-align:center; background:#eee; padding:5px; border-radius:5px;'><b>{name}</b></div>", unsafe_allow_html=True)

f_date_map = {}; s_date_map = {}
for e in period_fixed_events: f_date_map.setdefault(e.date, []).append(e)
for _, r in v_period_df.iterrows():
    s_date_map.setdefault(r["date"].date(), []).append((r["category"], r["amount"], r["memo"]))

for week in weeks:
    cols = st.columns(7)
    for idx, current_date in enumerate(week):
        if current_date is None:
            cols[idx].markdown("<div style='height:240px; background:#f9f9f9; border:1px solid #eee; border-radius:8px;'></div>", unsafe_allow_html=True)
            continue
        
        is_today = (current_date == actual_today)
        cell_html = [f"<div style='font-weight:bold; color:{'#2ecc71' if is_today else '#333'};'>{current_date.month}/{current_date.day} {'(오늘)' if is_today else ''}</div>"]
        
        # [수정] 일요일에 주간 잔액 표시 (식비는 이월 없이 해당 주만 계산)
        if idx == 6 or current_date == budget_end:
            if current_date in weekly_food_balances:
                bals = weekly_food_balances[current_date]
                cell_html.append(f"""
                <div style='margin-bottom:10px; padding:5px; background:#f1f9f4; border-radius:4px; font-size:10px; color:#27ae60; font-weight:bold; line-height:1.4;'>
                    🍞 주간 식비잔액: {bals['food']:,.0f}<br>
                    🧺 생활용품: {bals['household']:,.0f}<br>
                    🚗 차량/교통: {bals['transport']:,.0f}<br>
                    🚨 예비비: {bals['reserve']:,.0f}
                </div>
                """)

        # 비상금 인출 표시
        w_info = st.session_state.cash_data["monthly"].get(month_key, {})
        if w_info.get("withdrawal", 0) > 0:
            try:
                if dt.date.fromisoformat(w_info.get("withdrawal_date")) == current_date:
                    cell_html.append(f"<div style='background-color:#ff4b4b; color:white; padding:5px; border-radius:5px; font-weight:bold; text-align:center; font-size:11px; margin-bottom:8px;'>💸 비상금 인출: {w_info['withdrawal']:,.0f}원</div>")
            except: pass

        day_fixed = f_date_map.get(current_date, [])
        day_spent = s_date_map.get(current_date, [])
        if day_fixed:
            cell_html.append(f"<div style='color:#e74c3c; font-size:11px; font-weight:bold;'>고정: {sum(e.amount for e in day_fixed):,.0f}</div>")
            for e in day_fixed: cell_html.append(f"<div style='color:#c0392b; font-size:10px;'>· {e.item} ({e.amount:,.0f})</div>")
        if day_spent:
            cell_html.append(f"<div style='color:#3498db; font-size:11px; font-weight:bold; margin-top:5px;'>변동: {sum(a for _, a, _ in day_spent):,.0f}</div>")
            for c, a, m in day_spent:
                txt = m if m else c
                cell_html.append(f"<div style='color:#2980b9; font-size:10px;'>· {txt} ({a:,.0f})</div>")
        
        border_style = "4px solid #ccff00" if is_today else "1px solid #ddd"
        radius_style = "20px" if is_today else "8px"
        bg_color = "#fff4f4" if day_fixed else "#ffffff"
        cols[idx].markdown(f"<div style='height:240px; border: {border_style}; padding:8px; background:{bg_color}; border-radius:{radius_style}; overflow-y:auto;'>{''.join(cell_html)}</div>", unsafe_allow_html=True)

# -----------------------------
# 6. 상세 지출 내역 관리
# -----------------------------
st.markdown("---")
st.subheader("📜 기간 상세 지출 내역")
if not v_period_df.empty:
    st.data_editor(v_period_df.assign(date=v_period_df["date"].dt.date).sort_values("date"), use_container_width=True, hide_index=True)
    with st.expander("🗑️ 지출 항목 삭제", expanded=False):
        to_del = st.multiselect("삭제할 항목 선택", options=list(v_period_df.index), format_func=lambda x: f"{df.loc[x,'date'].date()} | {df.loc[x,'memo']} | {df.loc[x,'amount']:,}원")
        if st.button("선택한 항목 삭제"):
            st.session_state.df = st.session_state.df.drop(to_del).reset_index(drop=True)
            st.rerun()
