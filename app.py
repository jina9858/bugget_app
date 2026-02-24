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

# ---------- Sidebar (화면 모드 선택) ----------
st.sidebar.header("📱 디스플레이 설정")
view_mode = st.sidebar.radio("화면 모드 선택", ["PC 모드 (달력형)", "모바일 모드 (세로 리스트)"], index=0)

# 공통 및 모바일 전용 스타일 설정
st.markdown("""
    <style>
        .cal-content { font-size: 14px; line-height: 1.5; }
        .mobile-card {
            border-radius: 12px; padding: 15px; margin-bottom: 10px;
            border-left: 8px solid #eee; background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .today-card { border: 3px solid #ccff00 !important; }
        .fixed-badge { color: #e74c3c; font-weight: bold; font-size: 13px; }
        .spent-badge { color: #3498db; font-weight: bold; font-size: 13px; }
        .settle-box { background: #f1f9f4; border-radius: 8px; padding: 8px; margin-top: 5px; font-size: 12px; }
        [data-testid="stMetricValue"] { font-size: 20px !important; }
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
# 1. 데이터 관리 및 유틸리티
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
    if data: return [Event(date=dt.date.fromisoformat(r["date"]), category=r["category"], item=r["item"], amount=r["amount"], note=r.get("note","")) for r in data]
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
st.sidebar.header("⚙️ 예산 기간 설정")
selected_month = st.sidebar.selectbox("조회 월 선택", options=list(range(START_MONTH, END_MONTH + 1)), format_func=lambda m: f"{m}월")
month_key = f"{YEAR}-{selected_month:02d}"

saved_val = st.session_state.ref_dates.get(month_key, {"start": f"{YEAR}-{selected_month:02d}-01", "end": f"{YEAR}-{selected_month:02d}-24"})
budget_start = st.sidebar.date_input(f"📅 예산 시작일", value=dt.date.fromisoformat(saved_val["start"]))
budget_end = st.sidebar.date_input(f"🏁 예산 종료일", value=dt.date.fromisoformat(saved_val["end"]))

if budget_start.isoformat() != saved_val.get("start") or budget_end.isoformat() != saved_val.get("end"):
    st.session_state.ref_dates[month_key] = {"start": budget_start.isoformat(), "end": budget_end.isoformat()}
    save_json(REF_DATE_FILE, st.session_state.ref_dates); st.rerun()

st.sidebar.markdown("---")
food_budget_total = st.sidebar.number_input("🍔 월 식비", min_value=0, value=650000, step=10000)
hh_budget_total = st.sidebar.number_input("🧺 월 생활용품", min_value=0, value=100000, step=10000)
tr_budget_total = st.sidebar.number_input("🚗 월 차량/교통", min_value=0, value=150000, step=10000)
other_budget_total = st.sidebar.number_input("➕ 월 기타 예산", min_value=0, value=50000, step=10000)
em_budget_input = st.sidebar.number_input("🚨 월 예비비(기본)", min_value=0, value=200000, step=10000)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🅿️ 파킹 자산 관리")
cash_month_data = st.session_state.cash_data["monthly"].get(month_key, {"savings": 0, "withdrawal": 0, "withdrawal_date": budget_start.isoformat()})
monthly_savings = st.sidebar.number_input("이번 달 파킹(저금)", min_value=0, value=cash_month_data.get("savings", 0), step=10000)
withdrawal = st.sidebar.number_input("비상금 인출", min_value=0, value=cash_month_data.get("withdrawal", 0), step=10000)
withdrawal_date = st.sidebar.date_input("비상금 인출 날짜", value=dt.date.fromisoformat(cash_month_data.get("withdrawal_date", budget_start.isoformat())))

if st.sidebar.button("💰 자산 현황 업데이트"):
    old_data = st.session_state.cash_data["monthly"].get(month_key, {"savings": 0, "withdrawal": 0})
    diff = (monthly_savings - old_data.get("savings", 0)) - (withdrawal - old_data.get("withdrawal", 0))
    st.session_state.cash_data["total_balance"] += diff
    st.session_state.cash_data["monthly"][month_key] = {"savings": monthly_savings, "withdrawal": withdrawal, "withdrawal_date": withdrawal_date.isoformat()}
    save_json(CASH_ASSETS_FILE, st.session_state.cash_data); st.rerun()

with st.sidebar.expander("📝 수입/고정비 수정"):
    income_df = pd.DataFrame([{"월": k, "수입(원)": v} for k, v in st.session_state.income_data.items()])
    edited_inc = st.data_editor(income_df, use_container_width=True, hide_index=True)
    fixed_df = pd.DataFrame([{"date": e.date.isoformat(), "item": e.item, "amount": e.amount, "category": e.category} for e in st.session_state.fixed_events])
    edited_fixed = st.data_editor(fixed_df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 모든 정보 저장"):
        st.session_state.income_data = dict(zip(edited_inc["월"], edited_inc["수입(원)"]))
        save_json(INCOME_FILE, st.session_state.income_data)
        new_f = [Event(dt.date.fromisoformat(r["date"]), r["category"], r["item"], r["amount"]) for r in edited_fixed.to_dict(orient="records")]
        st.session_state.fixed_events = new_f
        save_json(FIXED_FILE, [{"date": e.date.isoformat(), "category": e.category, "item": e.item, "amount": e.amount} for e in new_f])
        st.rerun()

# -----------------------------
# 3. 집계 및 아구 맞추기 로직
# -----------------------------
df = st.session_state.df.copy()
cur_inc = st.session_state.income_data.get(month_key, 0)
period_fixed = [e for e in st.session_state.fixed_events if budget_start <= e.date <= budget_end]
paid_fixed_sum = sum(e.amount for e in period_fixed if e.date <= actual_today)
rem_fixed_sum = sum(e.amount for e in period_fixed if e.date > actual_today)

# [아구 맞추기] 남은 돈은 예비비로 자동 할당
total_budgetable = cur_inc - monthly_savings - (paid_fixed_sum + rem_fixed_sum) + withdrawal
init_plan = food_budget_total + hh_budget_total + tr_budget_total + other_budget_total + em_budget_input
surplus = total_budgetable - init_plan
em_budget_total = em_budget_input + (surplus if surplus > 0 else 0)

v_period_df = df[(df["date"].dt.date >= budget_start) & (df["date"].dt.date <= budget_end)]
total_balance = total_budgetable - int(v_period_df["amount"].sum())

# 주간 계산용 그리드
date_list = []
curr = budget_start
while curr <= budget_end: date_list.append(curr); curr += dt.timedelta(days=1)
weeks = [date_list[i:i+7] for i in range(0, len(date_list), 7)]

# -----------------------------
# 4. 상단 대시보드 (메트릭)
# -----------------------------
st.title(f"📅 {selected_month}월 예산 관리 ({view_mode})")

with st.expander("➕ 지출 추가하기", expanded=(view_mode == "PC 모드 (달력형)")):
    c1, c2, c3, c4 = st.columns([1.2, 1.0, 2.0, 1.0])
    with c1: d = st.date_input("날짜", value=budget_start)
    with c2: cat = st.selectbox("분류", ["식비", "생활용품", "교통/차량", "기타", "예비비"])
    with c3: memo = st.text_input("내용")
    with c4: amt = st.number_input("금액(원)", min_value=0, step=1000)
    if st.button("지출 추가"):
        if amt > 0:
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([{"date": pd.to_datetime(d), "category": cat, "memo": memo, "amount": int(amt)}])], ignore_index=True); st.rerun()

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("월 수입", f"{cur_inc:,.0f}원")
m2.metric("💰 총 현금 자산", f"{st.session_state.cash_data['total_balance']:,.0f}원", delta=f"- {withdrawal:,.0f}" if withdrawal > 0 else None, delta_color="normal")
m3.metric("✅ 나간 고정비", f"{paid_fixed_sum:,.0f}원")
m4.metric("⏳ 남은 고정비", f"{rem_fixed_sum:,.0f}원")
m5.metric("현재 가용 잔액", f"{total_balance:,.0f}원", delta=f"+ {withdrawal:,.0f}" if withdrawal > 0 else None)

if surplus > 0: st.info(f"💡 가용 자금 중 남는 **{surplus:,.0f}원**을 예비비에 자동 할당했습니다. (아구 맞춤 완료)")

# -----------------------------
# 5. 메인 레이아웃 (모드별 분기)
# -----------------------------
if view_mode == "PC 모드 (달력형)":
    # --- 기존 PC 달력형 레이아웃 ---
    header_cols = st.columns(7)
    for idx, name in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
        header_cols[idx].markdown(f"<div style='text-align:center; background:#eee; padding:5px; border-radius:5px;'><b>{name}</b></div>", unsafe_allow_html=True)
    
    f_map = {}; s_map = {}
    for e in period_fixed: f_map.setdefault(e.date, []).append(e)
    for _, r in v_period_df.iterrows(): s_map.setdefault(r["date"].date(), []).append(r)

    weeks_grid = [([None]*budget_start.weekday() + date_list)[i:i+7] for i in range(0, len([None]*budget_start.weekday() + date_list), 7)]
    for week in weeks_grid:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day is None: cols[idx].write(""); continue
            
            is_today = (day == actual_today)
            cell = [f"<div class='cal-content'><b style='color:{'#2ecc71' if is_today else '#333'};'>{day.month}/{day.day}</b>"]
            
            if withdrawal > 0 and dt.date.fromisoformat(withdrawal_date.isoformat()) == day:
                cell.append(f"<div style='background:#ff4b4b; color:white; padding:2px; border-radius:4px; font-size:11px; text-align:center;'>💸 비상금:{withdrawal:,.0f}</div>")
            
            day_f = f_map.get(day, []); day_s = s_map.get(day, [])
            if day_f: cell.append(f"<div class='fixed-badge'>고정:{sum(e.amount for e in day_f):,.0f}</div>")
            if not day_s.empty if isinstance(day_s, pd.DataFrame) else day_s:
                cell.append(f"<div class='spent-badge'>변동:{sum(r['amount'] for r in day_s):,.0f}</div>")
            
            cell.append("</div>")
            bg = "#fff4f4" if day_f else "white"
            cols[idx].markdown(f"<div style='height:180px; border: {'4px solid #ccff00' if is_today else '1px solid #ddd'}; padding:8px; background:{bg}; border-radius:10px; overflow-y:auto;'>{''.join(cell)}</div>", unsafe_allow_html=True)

else:
    # --- [신규] 모바일 세로 리스트 레이아웃 ---
    st.markdown("### 📱 일자별 지출 내역 (세로 리스트)")
    
    # 지출 데이터를 날짜별로 그룹화
    f_map = {}; s_map = {}
    for e in period_fixed: f_map.setdefault(e.date, []).append(e)
    for _, r in v_period_df.iterrows(): s_map.setdefault(r["date"].date(), []).append(r)

    # 예산 기간 내의 모든 날짜를 역순(최신순) 혹은 정순으로 표시
    for day in date_list:
        is_today = (day == actual_today)
        day_f = f_map.get(day, [])
        day_s = s_map.get(day, [])
        
        # 데이터가 있는 날짜만 강조해서 보여주기 위해 조건 설정 (진아님이 보기 편하게 모든 날짜 표시)
        today_class = "today-card" if is_today else ""
        
        with st.container():
            # 카드 형태의 HTML 구성
            f_total = sum(e.amount for e in day_f)
            s_total = sum(r['amount'] for r in day_s) if not (isinstance(day_s, list) and len(day_s)==0) else 0
            
            # 고정비나 변동비가 있으면 배경색 약간 변경
            border_color = "#e74c3c" if day_f else ("#3498db" if s_total > 0 else "#eee")
            
            html = f"""
            <div class="mobile-card {today_class}" style="border-left-color: {border_color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <b style="font-size: 16px;">{day.strftime('%m/%d')} ({['월','화','수','목','금','토','일'][day.weekday()]}) {'<span style="color:#2ecc71;">[오늘]</span>' if is_today else ''}</b>
                    <span style="font-size: 12px; color: #666;">일일 합계: {f_total + s_total:,.0f}원</span>
                </div>
            """
            
            if withdrawal > 0 and withdrawal_date == day:
                html += f"<div style='background:#ff4b4b; color:white; padding:5px; border-radius:6px; font-size:12px; margin:5px 0;'>💸 비상금 인출: {withdrawal:,.0f}원</div>"
            
            if day_f:
                html += f"<div class='fixed-badge'>📌 고정비: {f_total:,.0f}원</div>"
                for e in day_f: html += f"<div style='font-size:11px; margin-left:10px;'>· {e.item}</div>"
            
            if s_total > 0:
                html += f"<div class='spent-badge'>🛒 변동비: {s_total:,.0f}원</div>"
                for r in day_s: html += f"<div style='font-size:11px; margin-left:10px;'>· {r['memo'] if r['memo'] else r['category']} ({r['amount']:,.0f})</div>"
            
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

# -----------------------------
# 6. 상세 지출 내역 및 삭제
# -----------------------------
st.markdown("---")
st.subheader("📜 전체 상세 지출 내역")
if not v_period_df.empty:
    st.data_editor(v_period_df.assign(date=v_period_df["date"].dt.date).sort_values("date", ascending=False), use_container_width=True, hide_index=True)
    with st.expander("🗑️ 지출 항목 삭제"):
        to_del = st.multiselect("삭제 항목 선택", options=list(v_period_df.index), format_func=lambda x: f"{df.loc[x,'date'].date()} | {df.loc[x,'memo']} | {df.loc[x,'amount']:,}원")
        if st.button("선택 삭제"):
            st.session_state.df = st.session_state.df.drop(to_del).reset_index(drop=True); st.rerun()
