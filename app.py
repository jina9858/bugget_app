# ... (앞부분 생략) ...

# 달력 렌더링 부분 (이 부분을 찾아서 교체하세요)
days = ["월", "화", "수", "목", "금", "토", "일"]
cols = st.columns(7)
for i, d_name in enumerate(days): 
    cols[i].markdown(f"<div style='text-align:center;'><b>{d_name}</b></div>", unsafe_allow_html=True)

for week in weeks:
    cols = st.columns(7)
    for i, daynum in enumerate(week):
        if daynum == 0:
            cols[i].markdown("<div style='height:150px; background:#f0f2f6; border-radius:5px;'></div>", unsafe_allow_html=True)
            continue
        
        f_list = f_map.get(daynum, [])
        s_list = s_map.get(daynum, [])
        f_sum = sum(e.amount for e in f_list)
        s_sum = sum(a for _, a, _ in s_list)
        
        # 날짜 표시
        content = [f"<div style='font-weight:bold; border-bottom:1px solid #eee; margin-bottom:5px;'>{daynum}</div>"]
        
        # 고정비 상세 내역 추가
        if f_list:
            content.append(f"<div style='color:#e74c3c; font-size:11px; font-weight:bold;'>고정: {f_sum:,.0f}</div>")
            for e in f_list:
                content.append(f"<div style='color:#636e72; font-size:10px; line-height:1.2;'>· {e.item}</div>")
        
        # 변동지출(직접 입력) 상세 내역 추가
        if s_list:
            content.append(f"<div style='color:#3498db; font-size:11px; font-weight:bold; margin-top:5px;'>변동: {s_sum:,.0f}</div>")
            for cat, amt, memo in s_list:
                display_text = memo if memo else cat
                content.append(f"<div style='color:#636e72; font-size:10px; line-height:1.2;'>· {display_text}</div>")
        
        # 배경색 설정 (고정비 있는 날은 연한 분홍색)
        bg = "#fff" if not f_list else "#fff4f4"
        
        cols[i].markdown(f"""
            <div style="height:150px; border:1px solid #ddd; padding:8px; background:{bg}; border-radius:8px; overflow-y:auto;">
                {"".join(content)}
            </div>
        """, unsafe_allow_html=True)

# ... (뒷부분 생략) ...
