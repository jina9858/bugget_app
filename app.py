import streamlit as st
import pandas as pd
import calendar
import datetime as dt
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple

# 0. 페이지 기본 설정
st.set_page_config(page_title="예산 관리자", layout="wide")

# ---------- Sidebar (화면 모드 및 설정) ----------
st.sidebar.header("📱 디스플레이 설정")
view_mode = st.sidebar.radio("화면 모드 선택", ["PC 모드 (기존 달력)", "모바일 모드 (세로 카드)"], index=0)

# [수정] 전체적인 글자 크기를 줄이기 위한 CSS
st.markdown("""
    <style>
        .cal-content { font-size: 13px !important; line-height: 1.4; }
        .mobile-card {
            border-radius: 10px; padding: 12px; margin-bottom: 8px;
            border-left: 6px solid #eee; background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .today-card { border: 2px solid #ccff00 !important; }
        /* 메트릭 글자 크기 축소 */
        [data-testid="stMetricValue"] { font-size: 18px !important; }
        [data-testid="stMetricLabel"] { font-size: 13px !important; }
        /* 전체 텍스트 크기 미세 조정 */
        html, body, [class*="css"] { font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

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
            with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
        except: return default_val
    return default_val

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

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
        # [수정] image_42ac4e.png 에러 원인이 된 괄호 오타 수정
        return [Event(date=dt.date.fromisoformat(r["date"]), category=r["category"], item=r["item"], amount=r["amount"], note=r.get("note","")) for r in data]
    base = build_fixed_events()
    save_json(FIXED_FILE, [{"date": e.date.isoformat(), "category": e.category, "item": e.item, "amount": e.amount, "note": e.note} for e in base])
    return base

# -----------------------------
# 2. 세션 상태 및 날짜 (2026-02-24)
# -----------------------------
actual_today = dt.date(2026, 2, 24)

if "income_data" not in st.session_state: st.session_state.income_data = load_json(INCOME_FILE, {f"{YEAR}-{m:02d}": 0 for m in range(START_MONTH, END_MONTH + 1)})
if "fixed_events" not in st.session_state: st.session_state.fixed_events = load_fixed_events()
if "ref_dates" not in st.session_state: st.session_state.ref_dates = load_json(REF_DATE_FILE, {})
if "cash_data" not in st.session_state: st.session_state.cash_data = load_json(CASH_ASSETS_FILE, {"total_balance": 0, "monthly": {}})
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["date", "category", "memo", "amount"])
    st.session_state.df["date"] = pd.to_datetime(st.session_state.df["date"])

# ---------- Sidebar 상세 설정 ----------
st.sidebar.markdown("---")
st.sidebar.header("⚙️ 예산 설정")
selected_month = st.sidebar.selectbox("조회 월 선택", options=list(range(START_MONTH, END_MONTH + 1)), format_func=lambda m: f"{m}월")
month_key = f"{YEAR}-{selected_month:02d}"

saved_val = st.session_state.ref_dates.get(month_key, {"start": f"{YEAR}-{selected_month:02d}-01", "end": f"{YEAR}-{selected_month:02d}-24"})
budget_start = st.sidebar.date_input("📅 예산 시작일", value=dt.date.fromisoformat(saved_val["start"]))
budget_end = st.sidebar.date_input("🏁 예산 종료일", value=dt.date.fromisoformat(saved_val["end"]))

if budget_start.isoformat() != saved_val["start"] or budget_end.isoformat() != saved_val["end"]:
    st.session_state.ref_dates[month_key] = {"start": budget_start.isoformat(), "end": budget_end.isoformat()}
    save_json(REF_DATE_FILE, st.session_state.ref_dates); st.rerun()

food_budget_total = st.sidebar.number_input("🍔 월 식비", min_value=0, value=650000)
hh_budget_total = st.sidebar.number_input("🧺 월 생활용품", min_value=0, value=100000)
tr_budget_total = st.sidebar.number_input("🚗 월 차량/교통", min_value=0, value=150000)
other_budget_total = st.sidebar.number_input("➕ 월 기타", min_value=0, value=50000)
em_budget_input = st.sidebar.number_input("🚨 월 예비비(기본)", min_value=0, value=200000)

st.sidebar.markdown("---")
cash_info = st.session_state.cash_data["monthly"].get(month_key, {"savings": 0, "withdrawal": 0, "withdrawal_date": budget_start.isoformat()})
monthly_savings = st.sidebar.number_input("파킹(저금)", min_value=0, value=cash_info["savings"])
withdrawal = st.sidebar.number_input("비상금 인출", min_value=0, value=cash_info["withdrawal"])
withdrawal_date = st.sidebar.date_input("비상금 인출일", value=dt.date.fromisoformat(cash_info.get("withdrawal_date", budget_start.isoformat())))

if st.sidebar.button("💰 자산 현황 업데이트"):
    diff = (monthly_savings - cash_info["savings"]) - (withdrawal - cash_info["withdrawal"])
    st.session_state.cash_data["total_balance"] += diff
    st.session_state.cash_data["monthly"][month_key] = {"savings": monthly_savings, "withdrawal": withdrawal, "withdrawal_date": withdrawal_date.isoformat()}
    save_json(CASH_ASSETS_FILE, st.session_state.cash_data); st.rerun()

with st.sidebar.expander("📝 수입/고정비 수정"):
    inc_df = pd.DataFrame([{"월": k, "수입": v} for k, v in st.session_state.income_data.items()])
    edit_inc = st.data_editor(inc_df, use_container_width=True, hide_index=True)
    fix_df = pd.DataFrame([{"date": e.date.isoformat(), "item": e.item, "amount": e.amount, "category": e.category} for e in st.session_state.fixed_events])
    edit_fix = st.data_editor(fix_df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 정보 저장"):
        st.session_state.income_data = dict(zip(edit_inc["월"], edit_inc["수입"]))
        save_json(INCOME_FILE, st.session_state.income_data)
        new_f = [Event(dt.date.fromisoformat(r["date"]), r["category"], r["item"], r["amount"]) for r in edit_fix.to_dict(orient="records")]
        st.session_state.fixed_events = new_f
        save_json(FIXED_FILE, [{"date": e.date.isoformat(), "category": e.category, "item": e.item, "amount": e.amount} for e in new_f]); st.rerun()

# -----------------------------
# 3. 집계 및 계산 로직
# -----------------------------
df = st.session_state.df.copy()
cur_inc = st.session_state.income_data.get(month_key, 0)
p_fixed = [e for e in st.session_state.fixed_events if budget_start <= e.date <= budget_end]
paid_fixed = sum(e.amount for e in p_fixed if e.date <= actual_today)
rem_fixed = sum(e.amount for e in p_fixed if e.date > actual_today)

# 아구 맞추기 로직
total_budgetable = cur_inc - monthly_savings - (paid_fixed + rem_fixed) + withdrawal
init_plan = food_budget_total + hh_budget_total + tr_budget_total + other_budget_total + em_budget_input
surplus = total_budgetable - init_plan
em_budget_total = em_budget_input + (surplus if surplus > 0 else 0)

v_period_df = df[(df["date"].dt.date >= budget_start) & (df["date"].dt.date <= budget_end)]
total_balance = total_budgetable - int(v_period_df["amount"].sum())

# -----------------------------
# 4. 상단 대시보드 (에러 수정됨)
# -----------------------------
st.title(f"📅 {selected_month}월 예산 관리")

with st.expander("➕ 지출 추가하기", expanded=(view_mode == "PC 모드 (기존 달력)")):
    c1, c2, c3, c4 = st.columns([1.2, 1.0, 2.0, 1.0])
    with c1: d = st.date_input("날짜", value=budget_start)
    with c2: cat = st.selectbox("분류", ["식비", "생활용품", "교통/차량", "기타", "예비비"])
    with c3: memo = st.text_input("내용")
    with c4: amt = st.number_input("금액", min_value=0, step=1000)
    if st.button("추가"):
        if amt > 0:
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([{"date": pd.to_datetime(d), "category": cat, "memo": memo, "amount": int(amt)}])], ignore_index=True); st.rerun()

st.markdown("### 📊 자금 흐름 현황")
m1, m2, m3, m4, m5 = st.columns(5)
# [수정] image_43ab37.png 에러 원인이 된 f-string 오타 수정
m1.metric("월 수입", f"{cur_inc:,.0f}원")
m2.metric("💰 총 현금 자산", f"{st.session_state.cash_data['total_balance']:,.0f}원", delta=f"- {withdrawal:,.0f}" if withdrawal > 0 else None, delta_color="normal")
m3.metric("✅ 나간 고정비", f"{paid_fixed:,.0f}원")
m4.metric("⏳ 남은 고정비", f"{rem_fixed:,.0f}원")
m5.metric("현재 가용 잔액", f"{total_balance:,.0f}원", delta=f"+ {withdrawal:,.0f}" if withdrawal > 0 else None)

if surplus > 0: st.info(f"💡 남는 자금 {surplus:,.0f}원을 예비비에 자동 할당했습니다.")

st.markdown("---")
st.markdown("### 🎯 항목별 정산 현황")
u_food = int(v_period_df[v_period_df["category"]=="식비"]["amount"].sum())
u_hh = int(v_period_df[v_period_df["category"]=="생활용품"]["amount"].sum())
u_tr = int(v_period_df[v_period_df["category"]=="교통/차량"]["amount"].sum())
u_ot = int(v_period_df[v_period_df["category"]=="기타"]["amount"].sum())
u_em = int(v_period_df[v_period_df["category"]=="예비비"]["amount"].sum())

b_cols = st.columns(6)
b_cols[0].metric("🍔 식비", f"{food_budget_total:,.0f}", delta=f"{food_budget_total - u_food:,.0f} 남음")
b_cols[1].metric("🧺 생활", f"{hh_budget_total:,.0f}", delta=f"{hh_budget_total - u_hh:,.0f} 남음")
b_cols[2].metric("🚗 차량", f"{tr_budget_total:,.0f}", delta=f"{tr_budget_total - u_tr:,.0f} 남음")
b_cols[3].metric("➕ 기타", f"{other_budget_total:,.0f}", delta=f"{other_budget_total - u_ot:,.0f} 남음")
b_cols[4].metric("🚨 예비", f"{em_budget_total:,.0f}", delta=f"{em_budget_total - u_em:,.0f} 남음")
b_cols[5].metric("✅ 정산합계", f"{total_balance:,.0f}원")

# -----------------------------
# 5. 메인 레이아웃 (모드별 분기)
# -----------------------------
st.markdown("---")
date_list = []
curr = budget_start
while curr <= budget_end: date_list.append(curr); curr += dt.timedelta(days=1)

if view_mode == "PC 모드 (기존 달력)":
    f_map = {}; s_map = {}
    for e in p_fixed: f_map.setdefault(e.date, []).append(e)
    for _, r in v_period_df.iterrows(): s_map.setdefault(r["date"].date(), []).append(r)
    
    weeks_grid = [([None]*budget_start.weekday() + date_list)[i:i+7] for i in range(0, len([None]*budget_start.weekday() + date_list), 7)]
    for week in weeks_grid:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day is None: cols[idx].write(""); continue
            is_today = (day == actual_today)
            day_f = f_map.get(day, []); day_s = s_map.get(day, [])
            cell = [f"<div class='cal-content'><b style='color:{'#2ecc71' if is_today else '#333'};'>{day.month}/{day.day}</b>"]
            if withdrawal > 0 and withdrawal_date == day: cell.append(f"<div style='background:#ff4b4b; color:white; padding:2px; font-size:10px; border-radius:4px;'>💸 비상금:{withdrawal:,.0f}</div>")
            if day_f: cell.append(f"<div style='color:#e74c3c; font-weight:bold;'>고정:{sum(e.amount for e in day_f):,.0f}</div>")
            if day_s: cell.append(f"<div style='color:#3498db; font-weight:bold;'>변동:{sum(r['amount'] for r in day_s):,.0f}</div>")
            cell.append("</div>")
            cols[idx].markdown(f"<div style='height:180px; border: {'3px solid #ccff00' if is_today else '1px solid #ddd'}; padding:6px; background:{'#fff4f4' if day_f else 'white'}; border-radius:10px; overflow-y:auto;'>{''.join(cell)}</div>", unsafe_allow_html=True)
else:
    # --- 모바일: 세로 리스트형 ---
    st.subheader("📱 일자별 지출 카드")
    f_map = {}; s_map = {}
    for e in p_fixed: f_map.setdefault(e.date, []).append(e)
    for _, r in v_period_df.iterrows(): s_map.setdefault(r["date"].date(), []).append(r)
    
    for day in date_list:
        is_today = (day == actual_today)
        day_f = f_map.get(day, []); day_s = s_map.get(day, [])
        if not day_f and not day_s and not is_today: continue 
        f_sum = sum(e.amount for e
