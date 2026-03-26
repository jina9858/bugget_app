import streamlit as st
import pandas as pd
import calendar
import datetime as dt
import json
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple

# 0. 페이지 기본 설정 및 [달력 전용 글씨 최적화 CSS]
st.set_page_config(page_title="예산 달력", layout="wide")

st.markdown("""
    <style>
        /* [추가됨] 왼쪽 사이드바 너비 넓게 펴주기 */
        section[data-testid="stSidebar"] {
            min-width: 340px !important;
        }

        /* 모바일에서 화면 절반을 차지하는 큰 제목 텍스트 사이즈만 축소 */
        h1 { font-size: 22px !important; }
        
        /* 줄바꿈 방지를 위해 3개 타이틀(h3) 기본 사이즈 지정 */
        h3 { font-size: 20px !important; }

        @media screen and (max-width: 600px) {
            h1 { font-size: 20px !important; margin-bottom: 5px !important; }
            /* 모바일 화면일 때만 3개 타이틀(h3) 사이즈를 14px로 줄이고 자간을 좁혀 한 줄에 쏙 들어가게 함 */
            h3 { font-size: 18px !important; letter-spacing: -0.5px !important; }
        }

        /* 원래 설정하신 달력 텍스트 및 숫자 크기 100% 유지 (절대 건드리지 않음) */
        .cal-content {
            font-size: 18px !important;
            line-height: 1.4;
        }
        [data-testid="stMetricValue"] {
            font-size: 18px !important;
        }
        
        /* 모바일 세로모드(Z플립) 전용 카드 스타일 */
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
    base =