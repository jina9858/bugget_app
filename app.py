import streamlit as st
import pandas as pd
import calendar
import datetime as dt
import json
import os
from dataclasses import dataclass
from typing import List

# 0. 페이지 기본 설정
st.set_page_config(page_title="예산 관리자", layout="wide")

# ---------- Sidebar (화면 모드 선택) ----------
st.sidebar.header("📱 디스플레이 설정")
view_mode = st.sidebar.radio("화면 모드 선택", ["PC 모드 (기본 달력)", "모바일 모드 (세로 리스트)"], index=0)

# 폰트 사이즈 및 CSS 설정 (건드리지 않음)
st.markdown("""
    <style>
        /* 모바일에서 화면 절반을 차지하던 큰 제목(h1)만 크기 조절 */
        h1 { font-size: 26px !important; }
        h2 { font-size: 20px !important; }
        h3 { font-size: 18px !important; }
        @media screen and (max-width: 600px) {
            h1 { font-size: 22px !important; margin-bottom: 5px !important; }
            h2 { font-size: 18px !important; }
            h3 { font-size: 16px !important; }
        }

        /* 달력 내부 텍스트 및 기본 숫자 크기 */
        .cal-content { font-size: 14px !important; line-height: 1.4; }
        [data-testid="stMetricValue"] { font-size: 22px !important; }
        
        /* 모바일 카드 스타일 */
        .mobile-card {
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 12px;
            background-color: #ffffff;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        .mobile-today {
            border: 2px solid #ccff00 !important;
            background-color: #fcfdf7 !important;
        }
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
        return [Event(date=dt.date.fromisoformat(r["date"]), category=r["category"], item=r["item"], amount=r["amount"], note=r.get("note", "")) for r in data]
    base = build_fixed_events()
    save_json(FIXED_FILE, [{"date": e.date.isoformat(), "category": e.category, "item": e.item, "amount": e.amount, "note": e.note} for e in base])
    return base

# -----------------------------
# 2. 세션 상태 및 날짜 설정
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

with st.sidebar.expander("📝 수입/고정비 항목 수정"):
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
# 3. 집계 및 아구 맞추기 로직
# -----------------------------
df = st.session_state.df.copy()
cur_inc = st.session_state.income_data.get(month_key, 0)

period_fixed_events = [e for e in st.session_state.fixed_events if budget_start <= e.date <= budget_end]
paid_fixed_sum = sum(e.amount for e in period_fixed_events if e.date <= actual_today)
rem_fixed_sum = sum(e.amount for e in period_fixed_events if e.date > actual_today)

total_budgetable = cur_inc - monthly_savings - (paid_fixed_sum + rem_fixed_sum) + withdrawal
init_plan = food_budget_total + hh_budget_total + tr_budget_total + other_budget_total + em_budget_input
surplus = total_budgetable - init_plan
em_budget_total = em_budget_input + (surplus if surplus > 0 else 0)

v_period_df = df[(df["date"].dt.date >= budget_start) & (df["date"].dt.date <= budget_end)]
total_balance = total_budgetable - int(v_period_df["amount"].sum())

# 공통 달력 및 지출 매핑 데이터 생성
date_list = []
curr = budget_start
while curr <= budget_end: 
    date_list.append(curr)
    curr += dt.timedelta(days=1)

f_date_map = {}
s_date_map = {}
for e in period_fixed_events: 
    f_date_map.setdefault(e.date, []).append(e)
for _, r in v_period_df.iterrows(): 
    s_date_map.setdefault(r["date"].date(), []).append(r)

# -----------------------------
# 4. 상단 대시보드
# -----------------------------
st.title(f"📅 {selected_month}월 예산 관리")

st.markdown("### 📊 자금 흐름 현황")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("월 수입", f"{cur_inc:,.0f}원")
m2.metric("💰 총 현금 자산", f"{st.session_state.cash_data['total_balance']:,.0f}원", delta=f"- {withdrawal:,.0f}" if withdrawal > 0 else None, delta_color="normal")
m3.metric("✅ 나간 고정비", f"{paid_fixed_sum:,.0f}원")
m4.metric("⏳ 남은 고정비", f"{rem_fixed_sum:,.0f}원")
m5.metric("현재 가용 잔액", f"{total_balance:,.0f}원", delta=f"+ {withdrawal:,.0f}" if withdrawal > 0 else None)

if surplus > 0: 
    st.info(f"💡 가용 자금 중 남는 {surplus:,.0f}원을 예비비에 자동 할당하여 아구를 맞췄습니다.")

st.markdown("---")
st.markdown("### 🎯 항목별 정산 현황 (6컬럼)")
u_food = int(v_period_df[v_period_df["category"]=="식비"]["amount"].sum())
u_hh = int(v_period_df[v_period_df["category"]=="생활용품"]["amount"].sum())
u_tr = int(v_period_df[v_period_df["category"]=="교통/차량"]["amount"].sum())
u_ot = int(v_period_df[v_period_df["category"]=="기타"]["amount"].sum())
u_em = int(v_period_df[v_period_df["category"]=="예비비"]["amount"].sum())

b_cols = st.columns(6)
b_cols[0].metric("🍔 식비", f"{food_budget_total:,.0f}", delta=f"{food_budget_total - u_food:,.0f} 남음")
b_cols[1].metric("🧺 생활용품", f"{hh_budget_total:,.0f}", delta=f"{hh_budget_total - u_hh:,.0f} 남음")
b_cols[2].metric("🚗 차량/교통", f"{tr_budget_total:,.0f}", delta=f"{tr_budget_total - u_tr:,.0f} 남음")
b_cols[3].metric("➕ 기타", f"{other_budget_total:,.0f}", delta=f"{other_budget_total - u_ot:,.0f} 남음")
b_cols[4].metric("🚨 예비비", f"{em_budget_total:,.0f}", delta=f"{em_budget_total - u_em:,.0f} 남음")
b_cols[5].metric("✅ 정산총합", f"{total_balance:,.0f}원")

# -----------------------------
# 5. 메인 레이아웃 (모드 분기 처리)
# -----------------------------
st.markdown("---")

# [위치 변경됨] '지출 추가하기' 기능을 달력 바로 위로 옮겼습니다! (내부 코드는 100% 동일)
with st.expander("➕ 지출 추가하기", expanded=(view_mode == "PC 모드 (기본 달력)")):
    c1, c2, c3, c4 = st.columns([1.2, 1.0, 2.0, 1.0])
    with c1: d = st.date_input("날짜", value=budget_start)
    with c2: cat = st.selectbox("분류", ["식비", "생활용품", "교통/차량", "기타", "예비비"])
    with c3: memo = st.text_input("내용")
    with c4: amt = st.number_input("금액", min_value=0, step=1000)
    if st.button("추가"):
        if amt > 0:
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([{"date": pd.to_datetime(d), "category": cat, "memo": memo, "amount": int(amt)}])], ignore_index=True); st.rerun()


if view_mode == "PC 모드 (기본 달력)":
    st.subheader("🗓️ 지출 달력")
    st.caption(f"📍 오늘은 {actual_today.strftime('%m월 %d일')}입니다. 연두색 테두리로 표시됩니다.")
    
    header_cols = st.columns(7)
    for idx, name in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
        header_cols[idx].markdown(f"<div style='text-align:center; background:#eee; padding:5px; border-radius:5px;'><b>{name}</b></div>", unsafe_allow_html=True)
    
    weeks_grid = [([None]*budget_start.weekday() + date_list)[i:i+7] for i in range(0, len([None]*budget_start.weekday() + date_list), 7)]
    
    weekly_food_base = food_budget_total / len(weeks_grid)
    weekly_balances = {}
    for week_row in weeks_grid:
        valid = [d for d in week_row if d is not None]
        if not valid: continue
        ws, we = valid[0], valid[-1]
        w_food_spent = int(v_period_df[(v_period_df["category"] == "식비") & (v_period_df["date"].dt.date >= ws) & (v_period_df["date"].dt.date <= we)]["amount"].sum())
        w_food_bal = weekly_food_base - w_food_spent
        cum_spent_df = v_period_df[v_period_df["date"].dt.date <= we]
        weekly_balances[week_row[6] if (len(week_row) > 6 and week_row[6]) else we] = {
            "food": w_food_bal,
            "hh": hh_budget_total - int(cum_spent_df[cum_spent_df["category"] == "생활용품"]["amount"].sum()),
            "tr": tr_budget_total - int(cum_spent_df[cum_spent_df["category"] == "교통/차량"]["amount"].sum()),
            "other": other_budget_total - int(cum_spent_df[cum_spent_df["category"] == "기타"]["amount"].sum()),
            "em": em_budget_total - int(cum_spent_df[cum_spent_df["category"] == "예비비"]["amount"].sum())
        }

    for week in weeks_grid:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day is None: 
                cols[idx].markdown("<div style='height:280px; background:#f9f9f9; border:1px solid #eee; border-radius:8px;'></div>", unsafe_allow_html=True)
                continue
            
            is_today = (day == actual_today)
            day_f = f_date_map.get(day, [])
            day_s = s_date_map.get(day, [])
            
            cell = [f"<div class='cal-content'><div style='font-weight:bold; color:{'#2ecc71' if is_today else '#333'};'>{day.month}/{day.day} {'(오늘)' if is_today else ''}</div>"]
            
            if withdrawal > 0 and dt.date.fromisoformat(withdrawal_date.isoformat()) == day: 
                cell.append(f"<div style='background-color:#ff4b4b; color:white; padding:5px; border-radius:5px; font-weight:bold; text-align:center; font-size:13px; margin-bottom:8px;'>💸 비상금 인출: {withdrawal:,.0f}원</div>")
            
            if idx == 6 or day == budget_end:
                if day in weekly_balances:
                    b = weekly_balances[day]
                    def get_color(val): return "#e74c3c" if val < 0 else "#27ae60"
                    cell.append(f"""
                    <div style='margin-bottom:10px; padding:5px; background:#f1f9f4; border-radius:4px; font-size:12px; font-weight:bold; line-height:1.4;'>
                        <span style='color:{get_color(b['food'])};'>🍞 주간 식비: {b['food']:,.0f}</span><br>
                        <span style='color:{get_color(b['hh'])};'>🧺 생활용품: {b['hh']:,.0f}</span><br>
                        <span style='color:{get_color(b['tr'])};'>🚗 차량/교통: {b['tr']:,.0f}</span><br>
                        <span style='color:{get_color(b['other'])};'>➕ 기타: {b['other']:,.0f}</span>
                    </div>
                    <div style='padding:5px; background:#fff3cd; border-radius:4px; font-size:12px; font-weight:bold; border: 1px solid #ffeeba;'>
                        <span style='color:{get_color(b['em'])};'>🚨 예비비: {b['em']:,.0f}</span>
                    </div>
                    """)

            if day_f: 
                cell.append(f"<div style='color:#e74c3c; font-size:13px; font-weight:bold;'>고정: {sum(e.amount for e in day_f):,.0f}</div>")
                for e in day_f: cell.append(f"<div style='color:#c0392b; font-size:11px;'>· {e.item} ({e.amount:,.0f})</div>")
            if day_s: 
                cell.append(f"<div style='color:#3498db; font-size:13px; font-weight:bold; margin-top:5px;'>변동: {sum(r['amount'] for r in day_s):,.0f}</div>")
                for r in day_s: 
                    m_txt = r['memo'] if r['memo'] else r['category']
                    cell.append(f"<div style='color:#2980b9; font-size:11px;'>· {m_txt} ({r['amount']:,.0f})</div>")
            
            cell.append("</div>")
            border_sty = '4px solid #ccff00' if is_today else '1px solid #ddd'
            bg_col = '#fff4f4' if day_f else '#ffffff'
            rad_sty = '20px' if is_today else '8px'
            
            cols[idx].markdown(f"<div style='height:280px; border: {border_sty}; padding:8px; background:{bg_col}; border-radius:{rad_sty}; overflow-y:auto;'>{''.join(cell)}</div>", unsafe_allow_html=True)

else:
    st.subheader("📱 일자별 지출 내역 (모바일 리스트)")
    st.caption("내용이 있는 날짜와 오늘만 표시됩니다.")
    
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    w_info = st.session_state.cash_data["monthly"].get(month_key, {})
    
    for current_date in date_list:
        is_today = (current_date == actual_today)
        day_f = f_date_map.get(current_date, [])
        day_s = s_date_map.get(current_date, [])
        
        has_withdrawal = w_info.get("withdrawal", 0) > 0 and dt.date.fromisoformat(w_info.get("withdrawal_date")) == current_date
        
        if not day_f and not day_s and not is_today and not has_withdrawal: 
            continue 
            
        f_sum = sum(e.amount for e in day_f)
        s_sum = sum(r['amount'] for r in day_s)
        
        html_lines = []
        card_class = "mobile-card mobile-today" if is_today else "mobile-card"
        border_color = "#e74c3c" if day_f else "#3498db"
        
        html_lines.append(f"<div class='{card_class}' style='border-left: 6px solid {border_color};'>")
        
        today_badge = "<span style='color:#2ecc71; font-weight:bold; font-size:14px;'>[오늘]</span>" if is_today else ""
        html_lines.append(f"<div style='display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 8px;'>")
        html_lines.append(f"  <b style='font-size:18px; color:#333;'>{current_date.month}/{current_date.day} ({day_names[current_date.weekday()]}) {today_badge}</b>")
        if f_sum > 0 or s_sum > 0:
            html_lines.append(f"  <span style='font-size:14px; color:#555; font-weight:bold;'>일일 합계: {f_sum + s_sum:,.0f}원</span>")
        html_lines.append(f"</div>")
        
        if has_withdrawal:
            html_lines.append(f"<div style='background-color:#ff4b4b; color:white; padding:6px; border-radius:5px; font-weight:bold; text-align:center; font-size:13px; margin-bottom:8px;'>💸 비상금 인출: {w_info['withdrawal']:,.0f}원</div>")
        
        # 일요일 정산 박스
        if current_date.weekday() == 6 or current_date == budget_end:
            # 주간 정산 재계산 (모바일용)
            weeks_grid = [([None]*budget_start.weekday() + date_list)[i:i+7] for i in range(0, len([None]*budget_start.weekday() + date_list), 7)]
            weekly_food_base = food_budget_total / len(weeks_grid)
            w_bal = None
            for week_row in weeks_grid:
                valid = [d for d in week_row if d is not None]
                if not valid: continue
                if (week_row[6] if (len(week_row) > 6 and week_row[6]) else valid[-1]) == current_date:
                    ws, we = valid[0], valid[-1]
                    w_food_spent = int(v_period_df[(v_period_df["category"] == "식비") & (v_period_df["date"].dt.date >= ws) & (v_period_df["date"].dt.date <= we)]["amount"].sum())
                    w_food_bal = weekly_food_base - w_food_spent
                    cum_spent_df = v_period_df[v_period_df["date"].dt.date <= we]
                    w_bal = {
                        "food": w_food_bal,
                        "hh": hh_budget_total - int(cum_spent_df[cum_spent_df["category"] == "생활용품"]["amount"].sum()),
                        "tr": tr_budget_total - int(cum_spent_df[cum_spent_df["category"] == "교통/차량"]["amount"].sum()),
                        "other": other_budget_total - int(cum_spent_df[cum_spent_df["category"] == "기타"]["amount"].sum()),
                        "em": em_budget_total - int(cum_spent_df[cum_spent_df["category"] == "예비비"]["amount"].sum())
                    }
                    break
            
            if w_bal:
                def get_c(val): return "#e74c3c" if val < 0 else "#27ae60"
                html_lines.append(f"""
                <div style='margin-bottom:8px; padding:8px; background:#f1f9f4; border-radius:6px; font-size:13px; font-weight:bold; line-height:1.5;'>
                    <span style='color:{get_c(w_bal['food'])};'>🍞 주간 식비: {w_bal['food']:,.0f}</span><br>
                    <span style='color:{get_c(w_bal['hh'])};'>🧺 생활용품: {w_bal['hh']:,.0f}</span><br>
                    <span style='color:{get_c(w_bal['tr'])};'>🚗 차량/교통: {w_bal['tr']:,.0f}</span><br>
                    <span style='color:{get_c(w_bal['other'])};'>➕ 기타: {w_bal['other']:,.0f}</span>
                </div>
                <div style='padding:8px; background:#fff3cd; border-radius:6px; font-size:13px; font-weight:bold; border: 1px solid #ffeeba; margin-bottom:8px;'>
                    <span style='color:{get_c(w_bal['em'])};'>🚨 예비비: {w_bal['em']:,.0f}</span>
                </div>
                """)

        if day_f:
            html_lines.append(f"<div style='color:#e74c3c; font-size:14px; font-weight:bold; margin-top:4px;'>📌 고정 지출: {f_sum:,.0f}원</div>")
            for e in day_f:
                html_lines.append(f"<div style='color:#c0392b; font-size:13px; margin-left: 12px; margin-top:2px;'>· {e.item} ({e.amount:,.0f}원)</div>")
        
        if day_s:
            html_lines.append(f"<div style='color:#3498db; font-size:14px; font-weight:bold; margin-top:8px;'>🛒 변동 지출: {s_sum:,.0f}원</div>")
            for r in day_s:
                m_txt = r['memo'] if r['memo'] else r['category']
                html_lines.append(f"<div style='color:#2980b9; font-size:13px; margin-left: 12px; margin-top:2px;'>· {m_txt} ({r['amount']:,.0f}원)</div>")
        
        if not day_f and not day_s and not has_withdrawal and not (current_date.weekday() == 6 or current_date == budget_end):
            html_lines.append("<div style='color:#aaa; font-size:13px; text-align:center; padding: 10px 0;'>지출 내역 없음</div>")

        html_lines.append("</div>")
        st.markdown("".join(html_lines), unsafe_allow_html=True)

# -----------------------------
# 6. 상세 지출 내역 및 삭제 기능
# -----------------------------
st.markdown("---")
st.subheader("📜 기간 상세 지출 내역")
if not v_period_df.empty:
    st.data_editor(v_period_df.assign(date=v_period_df["date"].dt.date).sort_values("date"), use_container_width=True, hide_index=True)
    with st.expander("🗑️ 지출 항목 삭제", expanded=False):
        to_del = st.multiselect("삭제할 항목 선택", options=list(v_period_df.index), 
                                format_func=lambda x: f"{df.loc[x,'date'].date()} | {df.loc[x,'memo']} | {df.loc[x,'amount']:,}원")
        if st.button("선택한 항목 삭제"):
            st.session_state.df = st.session_state.df.drop(to_del).reset_index(drop=True); st.rerun()
