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

# 수입 (사용자 제공)
INCOME_BY_MONTH = {
    (YEAR, 2): 4_400_000,
    (YEAR, 3): 5_650_000,
    (YEAR, 4): 0,
    (YEAR, 5): 0,
    (YEAR, 6): 0,
}

# 예산(원)
MONTHLY_FOOD_BUDGET = 650_000
MONTHLY_EMERGENCY_BUDGET = 200_000

# 2월 컷오프 (2/22 이전 이미 출금 → 제외)
FEB_CUTOFF = dt.date(YEAR, 2, 22)

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
    # Mon=0 ... Sun=6
    if d.weekday() == 5:  # Sat
        return d + dt.timedelta(days=2)
    if d.weekday() == 6:  # Sun
        return d + dt.timedelta(days=1)
    return d

def build_fixed_events(year=YEAR, start_month=START_MONTH, end_month=END_MONTH) -> List[Event]:
    """
    기본 고정비 템플릿(초기값).
    이후에는 앱에서 편집 + 저장된 fixed_events.json을 우선 사용.
    """
    events: List[Event] = []
    for m in range(start_month, end_month + 1):
        # 고정비(기본)
        events += [
            Event(dt.date(year, m, 5),  "생활/구독", "금천누리복지 후원", 50_000, "정기 후원"),
            Event(dt.date(year, m, 9),  "통신",     "LGU+ 휴대폰",      19_220, "최근 평균"),
            Event(dt.date(year, m, 10), "공과금",   "도시가스",         70_913, "3개월 평균"),
            Event(dt.date(year, m, 10), "수수료",   "SMS 수수료",          300, "고정"),
            Event(dt.date(year, m, 12), "공과금",   "수도요금",         28_370, "평균치"),

            # 계돈/송금 (23~25일 → 대표일 23일로 표시)
            Event(dt.date(year, m, 23), "계돈/송금", "계돈(김아름)",     100_000, "23~25일"),
            Event(dt.date(year, m, 23), "계돈/송금", "정기송금(김주환)", 100_000, "23~25일"),
            Event(dt.date(year, m, 23), "계돈/송금", "계돈(우연지)",      30_000, "23~25일"),
            Event(dt.date(year, m, 23), "계돈/송금", "계돈(김영민)",      20_000, "23~25일"),

            # 25~26일 → 대표일 25일로 표시
            Event(dt.date(year, m, 25), "금융/보험", "교보생명",         212_108, "25~26일"),
            Event(dt.date(year, m, 25), "금융/보험", "농협생명",         136_200, "25~26일"),
            Event(dt.date(year, m, 25), "공과금",   "전기요금",          26_166, "25~26일"),

            # 카카오페이 운전자보험: 25일
            Event(dt.date(year, m, 25), "보험",     "카카오페이 운전자보험", 8_800, "매월 25일"),

            # 인터넷: 26일
            Event(dt.date(year, m, 26), "통신",     "LGU+ 인터넷",       32_830, "고정"),
        ]

        # 메리츠 운전자보험: 5일 주기(5/10/15/20/25/30)
        for dday in [5, 10, 15, 20, 25, 30]:
            if dday <= last_day(year, m):
                events.append(Event(dt.date(year, m, dday), "보험", "메리츠 운전자보험", 10_280, "5일 주기"))

        # 구독: 2월은 없음, 3월부터
        if m >= 3:
            events.append(Event(dt.date(year, m, 13), "생활/구독", "네이버 멤버십", 4_900, "다음구독 3/13"))
            events.append(Event(dt.date(year, m, 24), "생활/구독", "AI 구독",     30_000, "다음결제 3/24"))

        # 관리비: 월말, 주말이면 다음 월요일(다음달로 넘어갈 수 있음)
        ld = dt.date(year, m, last_day(year, m))
        debit = next_monday_if_weekend(ld)
        events.append(Event(debit, "주거/공과금", "관리비", 110_000, "월말(주말이면 다음월요일)"))

    # 2월 2/22 이전은 제외
    filtered: List[Event] = []
    for e in events:
        if e.date.year == YEAR and e.date.month == 2 and e.date < FEB_CUTOFF:
            continue
        filtered.append(e)
    return filtered

# -----------------------------
# 고정비 저장/불러오기(JSON)
# -----------------------------
FIXED_FILE = "fixed_events.json"

def events_to_dict(events: List[Event]) -> List[dict]:
    return [
        {
            "date": e.date.isoformat(),
            "category": e.category,
            "item": e.item,
            "amount": int(e.amount),
            "note": e.note,
        }
        for e in events
    ]

def dict_to_events(rows: List[dict]) -> List[Event]:
    out: List[Event] = []
    for r in rows:
        out.append(
            Event(
                date=dt.date.fromisoformat(str(r["date"])),
                category=str(r.get("category", "")),
                item=str(r.get("item", "")),
                amount=int(r.get("amount", 0) or 0),
                note=str(r.get("note", "")),
            )
        )
    return out

def save_fixed_events(events: List[Event]) -> None:
    with open(FIXED_FILE, "w", encoding="utf-8") as f:
        json.dump(events_to_dict(events), f, ensure_ascii=False, indent=2)

def load_fixed_events() -> List[Event]:
    if os.path.exists(FIXED_FILE):
        with open(FIXED_FILE, "r", encoding="utf-8") as f:
            rows = json.load(f)
        return dict_to_events(rows)

    # 처음 실행이면 기본값 생성 후 저장
    base = build_fixed_events()
    save_fixed_events(base)
    return base

# 전역 고정비 리스트(앱에서 편집 후 갱신)
FIXED_EVENTS: List[Event] = load_fixed_events()

def fixed_events_for_month(year: int, month: int) -> List[Event]:
    return [e for e in FIXED_EVENTS if e.date.year == year and e.date.month == month]

def fixed_total_for_month(year: int, month: int) -> int:
    return sum(e.amount for e in fixed_events_for_month(year, month))

# -----------------------------
# 지출 데이터 상태
# -----------------------------
def ensure_state():
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame(columns=["date", "category", "memo", "amount"])
        st.session_state.df["date"] = pd.to_datetime(st.session_state.df["date"])

ensure_state()

# ---------- Sidebar ----------
st.sidebar.header("설정")
month = st.sidebar.selectbox(
    "월 선택",
    options=list(range(START_MONTH, END_MONTH + 1)),
    format_func=lambda m: f"{m}월"
)
income = INCOME_BY_MONTH.get((YEAR, month), 0)
fixed_total = fixed_total_for_month(YEAR, month)

st.sidebar.markdown("### 예산(월)")
food_budget = st.sidebar.number_input("식비 예산", min_value=0, value=MONTHLY_FOOD_BUDGET, step=10_000)
em_budget = st.sidebar.number_input("예비비 예산", min_value=0, value=MONTHLY_EMERGENCY_BUDGET, step=10_000)

# --- 고정비 편집 ---
st.sidebar.markdown("### 고정비 편집")
with st.sidebar.expander("고정비 수정/추가/삭제 후 저장", expanded=False):
    fixed_df = pd.DataFrame([{
        "date": e.date.isoformat(),      # YYYY-MM-DD
        "category": e.category,
        "item": e.item,
        "amount": e.amount,
        "note": e.note
    } for e in FIXED_EVENTS])

    st.caption("※ date는 YYYY-MM-DD 형식(예: 2026-03-24). 금액은 숫자만.")
    edited = st.data_editor(
        fixed_df,
        use_container_width=True,
        num_rows="dynamic",
        key="fixed_editor"
    )

    cA, cB = st.columns(2)
    with cA:
        if st.button("✅ 고정비 저장"):
            try:
                tmp = edited.copy()

                # 유효성(최소) 체크 + 정리
                tmp["date"] = pd.to_datetime(tmp["date"]).dt.date.astype(str)
                tmp["amount"] = tmp["amount"].fillna(0).astype(int)
                tmp["category"] = tmp["category"].fillna("").astype(str)
                tmp["item"] = tmp["item"].fillna("").astype(str)
                tmp["note"] = tmp["note"].fillna("").astype(str)

                new_events = dict_to_events(tmp.to_dict(orient="records"))
                save_fixed_events(new_events)

                # 전역 리스트 갱신
                FIXED_EVENTS[:] = new_events
                st.success("저장 완료! 달력/고정비 합계에 즉시 반영됩니다.")
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

    with cB:
        if st.button("🔄 기본값으로 초기화"):
            base = build_fixed_events()
            save_fixed_events(base)
            FIXED_EVENTS[:] = base
            st.success("초기화 완료!")
            st.rerun()

# CSV 저장/불러오기 (지출)
st.sidebar.markdown("### 지출 데이터")
st.sidebar.download_button(
    "지출 CSV 다운로드(백업)",
    data=st.session_state.df.assign(date=st.session_state.df["date"].dt.date).to_csv(index=False).encode("utf-8-sig"),
    file_name="expenses.csv",
    mime="text/csv"
)

up = st.sidebar.file_uploader("CSV 업로드(복원)", type=["csv"])
if up is not None:
    try:
        tmp = pd.read_csv(up)
        tmp["date"] = pd.to_datetime(tmp["date"])
        tmp["amount"] = tmp["amount"].astype(int)
        st.session_state.df = tmp[["date", "category", "memo", "amount"]].copy()
        st.sidebar.success("CSV 복원 완료")
    except Exception as e:
        st.sidebar.error(f"업로드 실패: {e}")

# ---------- Main ----------
st.title(f"{YEAR}년 {month}월 예산 달력")

# 입력 폼
with st.expander("➕ 지출 입력", expanded=True):
    c1, c2, c3, c4 = st.columns([1.2, 1.0, 2.0, 1.0])
    with c1:
        d = st.date_input(
            "날짜",
            value=dt.date(YEAR, month, 1),
            min_value=dt.date(YEAR, START_MONTH, 1),
            max_value=dt.date(YEAR, END_MONTH, last_day(YEAR, END_MONTH))
        )
    with c2:
        cat = st.selectbox("분류", ["식비", "예비비", "기타"])
    with c3:
        memo = st.text_input("내용", placeholder="예: 장보기 / 커피 / 병원 / 택시 등")
    with c4:
        amt = st.number_input("금액(원)", min_value=0, step=1000, value=0)

    if st.button("추가하기"):
        if amt <= 0:
            st.warning("금액을 1원 이상 입력해줘.")
        else:
            new = pd.DataFrame([{
                "date": pd.to_datetime(d),
                "category": cat,
                "memo": memo.strip(),
                "amount": int(amt)
            }])
            st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True)
            st.success("추가 완료!")

# 월별 지출 집계
df = st.session_state.df.copy()
df["date"] = pd.to_datetime(df["date"])
month_df = df[(df["date"].dt.year == YEAR) & (df["date"].dt.month == month)].copy()

var_food = int(month_df.loc[month_df["category"] == "식비", "amount"].sum())
var_em   = int(month_df.loc[month_df["category"] == "예비비", "amount"].sum())
var_etc  = int(month_df.loc[month_df["category"] == "기타", "amount"].sum())
var_total = var_food + var_em + var_etc

fixed_total = fixed_total_for_month(YEAR, month)
remaining = income - fixed_total - var_total

# 요약 박스
s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("수입", f"{income:,.0f}원")
s2.metric("고정비(출금일 기준)", f"{fixed_total:,.0f}원")
s3.metric("변동지출(입력)", f"{var_total:,.0f}원")
s4.metric("월 잔액", f"{remaining:,.0f}원")
s5.metric("식비/예비비/기타", f"{var_food:,.0f} / {var_em:,.0f} / {var_etc:,.0f}원")

# 달력 표시
st.subheader("달력")
cal = calendar.Calendar(firstweekday=0)  # 월요일 시작
weeks = cal.monthdayscalendar(YEAR, month)

# 고정비 map
fixed_map: Dict[int, List[Event]] = {}
for e in fixed_events_for_month(YEAR, month):
    fixed_map.setdefault(e.date.day, []).append(e)

# 입력 지출 map
spent_map: Dict[int, List[Tuple[str, int, str]]] = {}
for _, r in month_df.iterrows():
    day = int(r["date"].day)
    spent_map.setdefault(day, []).append((r["category"], int(r["amount"]), str(r["memo"])))


# 요일 헤더
cols = st.columns(7)
for i, name in enumerate(["월","화","수","목","금","토","일"]):
    cols[i].markdown(f"**{name}**")

# 주차 rows
for week in weeks:
    cols = st.columns(7)
    for i, daynum in enumerate(week):
        if daynum == 0:
            cols[i].markdown(
                "<div style='height:150px; border:1px solid #eee; background:#f7f7f7'></div>",
                unsafe_allow_html=True
            )
            continue

        fixed_list = fixed_map.get(daynum, [])
        spent_list = spent_map.get(daynum, [])

        fixed_sum = sum(e.amount for e in fixed_list)
        spent_sum = sum(a for _, a, _ in spent_list)

        lines = [f"**{daynum}일**"]
        if fixed_list:
            lines.append(f"- 고정비: {fixed_sum:,.0f}원")
            for e in fixed_list[:6]:
                lines.append(f"  - {e.item} {e.amount:,.0f}")
            if len(fixed_list) > 6:
                lines.append(f"  - …(+{len(fixed_list)-6}개)")

        if spent_list:
            lines.append(f"- 입력지출: {spent_sum:,.0f}원")
            for c, a, m in spent_list[:6]:
                m = m if m else ""
                lines.append(f"  - [{c}] {a:,.0f} {m}")
            if len(spent_list) > 6:
                lines.append(f"  - …(+{len(spent_list)-6}건)")

        box_color = "#fff7e6" if fixed_list else "#ffffff"
        cols[i].markdown(
            f"<div style='height:150px; overflow:auto; border:1px solid #ddd; padding:8px; background:{box_color}; border-radius:8px;'>"
            + "<br>".join(lines) +
            "</div>",
            unsafe_allow_html=True
        )

st.subheader("이번 달 입력내역(수정/삭제)")
if month_df.empty:
    st.info("아직 입력된 지출이 없어.")
else:
    show = month_df.sort_values("date").copy()
    show["date"] = show["date"].dt.date
    st.dataframe(show, use_container_width=True, hide_index=True)

    st.caption("삭제하려면 아래에서 행을 선택 후 삭제 버튼을 누르세요.")
    idxs = st.multiselect(
        "삭제할 행 선택",
        options=list(show.index),
        format_func=lambda i: f"{show.loc[i,'date']} / {show.loc[i,'category']} / {show.loc[i,'amount']:,}원 / {show.loc[i,'memo']}"
    )
    if st.button("선택한 행 삭제"):
        st.session_state.df = st.session_state.df.drop(index=idxs).reset_index(drop=True)
        st.success("삭제 완료!")
        st.rerun()

st.caption("※ 팁: 지출은 CSV로 주기적으로 백업해두면 안전해요. 고정비는 '고정비 저장'을 누른 뒤 달력 반영을 확인하세요.")
