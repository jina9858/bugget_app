import streamlit as st
import pandas as pd
import calendar
import datetime as dt
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple

st.set_page_config(page_title="예산 달력", layout="wide")

YEAR = 2026
START_MONTH = 2
END_MONTH = 6
INCOME_FILE = "income_data.json"  # 수입 저장 파일
FIXED_FILE = "fixed_events.json"

# -----------------------------
# 수입(Income) 관리 로직
# -----------------------------
def load_income() -> Dict[str, int]:
    # 기본값
    default_income = {
        f"{YEAR}-02": 4_400_000,
        f"{YEAR}-03": 5_650_000,
        f"{YEAR}-04": 0,
        f"{YEAR}-05": 0,
        f"{YEAR}-06": 0,
    }
    if os.path.exists(INCOME_FILE):
        with open(INCOME_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return default_income

def save_income(income_dict: Dict[str, int]):
    with open(INCOME_FILE, "w", encoding="utf-8") as f:
        json.dump(income_dict, f, ensure_ascii=False, indent=2)

# 세션 상태에 수입 데이터 로드
if "income_data" not in st.session_state:
    st.session_state.income_data = load_income()

# -----------------------------
# 고정비(Fixed Events) 관리 로직
# -----------------------------
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
    # 2월 컷오프 (2/22 이전 이미 출금 → 제외)
    feb_cutoff = dt.date(YEAR, 2, 22)
    
    for m in range(start_month, end_month + 1):
        events += [
            Event(dt.date(year, m, 5),  "생활/구독", "금천누리복지 후원", 50_000, "정기 후원"),
            Event(dt.date(year, m, 9),  "통신",     "LGU+ 휴대폰",      19_220, "최근 평균"),
            Event(dt.date(year, m, 10), "공과금",   "도시가스",         70_913, "3개월 평균"),
            Event(dt.date(year, m, 10), "수수료",   "SMS 수수료",          300, "고정"),
            Event(dt.date(year, m, 12), "공과금",   "수도요금",         28_370, "평균치"),
            Event(dt.date(year, m, 23), "계돈/송금", "계돈(김아름)",     100_000, "23~25일"),
            Event(dt.date(year, m, 23), "계돈/송금", "정기송금(김주환)", 100_000, "23~25일"),
            Event(dt.date(year, m, 23), "계돈/송금", "계돈(우연지)",      30_000, "23~25일"),
            Event(dt.date(year, m, 23), "계돈/송금", "계돈(김영민)",      20_000, "23~25일"),
            Event(dt.date(year, m, 25), "금융/보험", "교보생명",         212_108, "25~26일"),
            Event(dt.date(year, m, 25), "금융/보험", "농협생명",         136_200, "25~26일"),
            Event(dt.date(year, m, 25), "공과금",   "전기요금",          26_166, "25~26일"),
            Event(dt.date(year, m, 25), "보험",     "카카오페이 운전자보험", 8_800, "매월 25일"),
            Event(dt.date(year, m, 26), "통신",     "LGU+ 인터넷",       32_830, "고정"),
        ]
        for dday in [5, 10, 15, 20, 25, 30]:
            if dday <= last_day(year, m):
                events.append(Event(dt.date(year, m, dday), "보험", "메리츠 운전자보험", 10_280, "5일 주기"))
        if m >= 3:
            events.append(Event(dt.date(year, m, 13), "생활/구독", "네이버 멤버십", 4_900, "다음구독 3/13"))
            events.append(Event(dt.date(year, m, 24), "생활/구독", "AI 구독",      30_000, "다음결제 3/24"))
        ld = dt.date(year, m, last_day(year, m))
        debit = next_monday_if_weekend(ld)
        events.append(Event(debit, "주거/공과금", "관리비", 110_000, "월말(주말이면 다음월요일)"))

    return [e for e in events if not (e.date.year == YEAR and e.date.month == 2 and e.date < feb_cutoff)]

def events_to_dict(events: List[Event]) -> List[dict]:
    return [{"date": e.date.isoformat(), "category": e.category, "item": e.item, "amount": int(e.amount), "note": e.note} for e in events]

def dict_to_events(rows: List[dict]) -> List[Event]:
    return [Event(date=dt.date.fromisoformat(str(r["date"])), category=str(r.get("category", "")), item=str(r.get("item", "")), amount=int(r.get("amount", 0) or 0), note=str(r.get("note", ""))) for r in rows]

def save_fixed_events(events: List[Event]) -> None:
    with open(FIXED_FILE, "w", encoding="utf-8") as f:
        json.dump(events_to_dict(events), f, ensure_ascii=False, indent=2)

def load_fixed_events() -> List[Event]:
    if os.path.exists(FIXED_FILE):
        with open(FIXED_FILE, "r", encoding="utf-8") as f:
            return dict_to_events(json.load(f))
    base = build_fixed_events()
    save_fixed_events(base)
    return base

# 데이터 초기 로드
FIXED_EVENTS = load_fixed_events()

# -----------------------------
# 지출 데이터 상태 관리
# -----------------------------
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["date", "category", "memo", "amount"])
    st.session_state.df["date"] = pd.to_datetime(st.session_state.df["date"])

# ---------- Sidebar ----------
st.sidebar.header("⚙️ 설정")
selected_month = st.sidebar.selectbox(
    "조회 월 선택",
    options=list(range(START_MONTH, END_MONTH + 1)),
    format_func=lambda m: f"{m}월"
)

# --- 수입 편집 섹션 ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 💰 수입 편집")
with st.sidebar.expander("월별 수입 수정", expanded=False):
    income_df = pd.DataFrame([
        {"월": k, "수입(원)": v} for k, v in st.session_state.income_data.items()
    ])
    edited_income = st.data_editor(income_df, use_container_width=True, hide_index=True)
    
    if st.button("수입 저장"):
        new_income_dict = dict(zip(edited_income["월"], edited_income["수입(원)"]))
        save_income(new_income_dict)
        st.session_state.income_data = new_income_dict
        st.success("수입 정보가 저장되었습니다!")
        st.rerun()

# 현재 선택된 월의 수입 가져오기
current_income = st.session_state.income_data.get(f"{YEAR}-{selected_month:02d}", 0)

# --- 예산 설정 ---
st.sidebar.markdown("### 📑 예산 설정")
food_budget = st.sidebar.number_input("식비 예산", min_value=0, value=650_000, step=10_000)
em_budget = st.sidebar.number_input("예비비 예산", min_value=0, value=200_000, step=10_000)

# --- 고정비 편집 ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠️ 고정비 관리")
with st.sidebar.expander("고정비 수정/추가/삭제", expanded=False):
    fixed_df_ui = pd.DataFrame([{"date": e.date.isoformat(), "category": e.category, "item": e.item, "amount": e.amount, "note": e.note} for e in FIXED_EVENTS])
    edited_fixed = st.data_editor(fixed_df_ui, use_container_width=True, num_rows="dynamic")

    col_save, col_reset = st.columns(2)
    with col_save:
        if st.button("✅ 고정비 저장"):
            try:
                new_evs = dict_to_events(edited_fixed.to_dict(orient="records"))
                save_fixed_events(new_evs)
                FIXED_EVENTS[:] = new_evs
                st.success("저장 완료!")
                st.rerun()
            except Exception as e: st.error(f"오류: {e}")
    with col_reset:
        if st.button("🔄 초기화"):
            base = build_fixed_events()
            save_fixed_events(base)
            st.rerun()

# 지출 백업/복원
st.sidebar.markdown("---")
st.sidebar.download_button("📥 지출 CSV 백업", data=st.session_state.df.to_csv(index=False).encode("utf-8-sig"), file_name="expenses.csv")
up = st.sidebar.file_uploader("📤 지출 CSV 복원", type=["csv"])
if up:
    st.session_state.df = pd.read_csv(up).assign(date=lambda x: pd.to_datetime(x["date"]))

# ---------- Main ----------
st.title(f"📅 {YEAR}년 {selected_month}월 예산 달력")

# 지출 입력 폼
with st.expander("➕ 새로운 지출 추가", expanded=True):
    c1, c2, c3, c4 = st.columns([1.2, 1.0, 2.0, 1.0])
    with c1: d = st.date_input("날짜", value=dt.date(YEAR, selected_month, 1))
    with c2: cat = st.selectbox("분류", ["식비", "예비비", "기타"])
    with c3: memo = st.text_input("내용", placeholder="지출 내역 요약")
    with c4: amt = st.number_input("금액(원)", min_value=0, step=1000)

    if st.button("지출 추가"):
        if amt > 0:
            new_row = pd.DataFrame([{"date": pd.to_datetime(d), "category": cat, "memo": memo.strip(), "amount": int(amt)}])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.success("지출이 추가되었습니다.")
            st.rerun()

# 데이터 집계
df = st.session_state.df.copy()
m_df = df[(df["date"].dt.year == YEAR) & (df["date"].dt.month == selected_month)]
v_food = int(m_df.loc[m_df["category"] == "식비", "amount"].sum())
v_em = int(m_df.loc[m_df["category"] == "예비비", "amount"].sum())
v_etc = int(m_df.loc[m_df["category"] == "기타", "amount"].sum())
v_total = v_food + v_em + v_etc

f_total = sum(e.amount for e in FIXED_EVENTS if e.date.year == YEAR and e.date.month == selected_month)
remaining = current_income - f_total - v_total

# 상단 요약 요약
s1, s2, s3, s4 = st.columns(4)
s1.metric("월 수입", f"{current_income:,.0f}원")
s2.metric("고정비 합계", f"{f_total:,.0f}원")
s3.metric("변동지출 합계", f"{v_total:,.0f}원")
s4.metric("남은 잔액", f"{remaining:,.0f}원", delta_color="normal")

# 달력 섹션
st.subheader("이번 달 지출 현황")
cal = calendar.Calendar(firstweekday=0)
weeks = cal.monthdayscalendar(YEAR, selected_month)

f_map = {}
for e in [x for x in FIXED_EVENTS if x.date.year == YEAR and x.date.month == selected_month]:
    f_map.setdefault(e.date.day, []).append(e)

s_map = {}
for _, r in m_df.iterrows():
    s_map.setdefault(int(r["date"].day), []).append((r["category"], r["amount"], r["memo"]))

# 달력 렌더링
days = ["월", "화", "수", "목", "금", "토", "일"]
cols = st.columns(7)
for i, d_name in enumerate(days): cols[i].markdown(f"**{d_name}**")

for week in weeks:
    cols = st.columns(7)
    for i, daynum in enumerate(week):
        if daynum == 0:
            cols[i].markdown("<div style='height:120px; background:#f0f2f6; border-radius:5px;'></div>", unsafe_allow_html=True)
            continue
        
        f_list = f_map.get(daynum, [])
        s_list = s_map.get(daynum, [])
        f_sum = sum(e.amount for e in f_list)
        s_sum = sum(a for _, a, _ in s_list)
        
        content = [f"**{daynum}**"]
        if f_list: content.append(f"<span style='color:red; font-size:12px;'>고정: {f_sum:,.0f}</span>")
        if s_list: content.append(f"<span style='color:blue; font-size:12px;'>변동: {s_sum:,.0f}</span>")
        
        bg = "#fff" if not f_list else "#fff4f4"
        cols[i].markdown(f"""
            <div style="height:120px; border:1px solid #ddd; padding:5px; background:{bg}; border-radius:5px; overflow-y:auto;">
                {"<br>".join(content)}
            </div>
        """, unsafe_allow_html=True)

# 지출 내역 관리
st.markdown("---")
st.subheader("지출 내역 상세")
if not m_df.empty:
    st.dataframe(m_df.assign(date=m_df["date"].dt.date).sort_values("date"), use_container_width=True, hide_index=True)
    
    with st.expander("지출 항목 삭제"):
        to_delete = st.multiselect("삭제할 항목을 선택하세요", options=m_df.index, 
                                   format_func=lambda x: f"{m_df.loc[x,'date'].date()} | {m_df.loc[x,'memo']} | {m_df.loc[x,'amount']:,}원")
        if st.button("선택 항목 삭제"):
            st.session_state.df = st.session_state.df.drop(to_delete).reset_index(drop=True)
            st.rerun()
else:
    st.info("입력된 지출 내역이 없습니다.")
