if st.sidebar.button("📌 예산 설정 저장"):
    st.session_state.ref_dates[month_key] = {
        "start": budget_start.isoformat(),
        "end": budget_end.isoformat()
    }
    save_json(REF_DATE_FILE, st.session_state.ref_dates)

    st.session_state.budget_settings[month_key] = {
        "food_budget_total": int(food_budget_total),
        "hh_budget_total": int(hh_budget_total),
        "tr_budget_total": int(tr_budget_total),
        "other_budget_total": int(other_budget_total),
        "em_budget_input": int(em_budget_input)
    }
    save_json(BUDGET_SETTINGS_FILE, st.session_state.budget_settings)
    st.sidebar.success("예산 설정 저장 완료")
    st.rerun()