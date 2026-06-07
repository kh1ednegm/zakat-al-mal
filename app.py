from datetime import date

import streamlit as st

from config import DISCLAIMER_AR, SCHOLARLY_LABELS
from database.session import get_session, init_db
from repositories.data_repository import DataRepository
from services.hijri_service import HijriService
from services.zakat_calculation_service import (
    DebtDeductionMode,
    GoldValuationMode,
    ZakatCalculationService,
)

RTL_CSS = """
<style>
    html, body, [class*="css"] {
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', Tahoma, 'Noto Sans Arabic', Arial, sans-serif;
    }
    .stApp {
        direction: rtl;
    }
    .stMetric {
        direction: rtl;
        text-align: right;
    }
    .scholarly-badge {
        background-color: #E8F5E9;
        border-right: 4px solid #1B5E20;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        direction: rtl;
        text-align: right;
    }
    .disclaimer {
        background-color: #FFF8E1;
        border-right: 4px solid #F9A825;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 16px 0;
        direction: rtl;
        text-align: right;
    }
    h1, h2, h3, h4, p, label, span, div {
        direction: rtl;
    }
    [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }
</style>
"""


def init_session_state() -> None:
    defaults = {
        "gold_price_per_gram": 250.0,
        "debt_mode": DebtDeductionMode.IMMEDIATE_ONLY.value,
        "gold_mode": GoldValuationMode.MARKET_PRICE.value,
        "unified_zakat_month": 9,
        "unified_zakat_day": 1,
        "calculation_date": date.today(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_method_result(result, key_prefix: str) -> None:
    st.markdown(
        f'<div class="scholarly-badge"><strong>رأي فقهي:</strong> {result.scholarly_opinion_label}</div>',
        unsafe_allow_html=True,
    )
    st.caption(result.explanation)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("إجمالي الثروة", f"{result.total_wealth:,.2f}")
    col2.metric("المال الخاضع للزكاة", f"{result.zakatable_wealth:,.2f}")
    col3.metric("المال غير الخاضع للزكاة", f"{result.non_zakatable_wealth:,.2f}")
    col4.metric("الديون المخصومة", f"{result.deductible_debts:,.2f}")

    col5, col6, col7 = st.columns(3)
    col5.metric("صافي المال الخاضع للزكاة", f"{result.net_zakatable_wealth:,.2f}")
    col6.metric("النصاب", f"{result.nisab_threshold:,.2f}")
    nisab_status = "بلغ النصاب ✓" if result.meets_nisab else "لم يبلغ النصاب"
    col7.metric("حالة النصاب", nisab_status)

    st.success(f"**مبلغ الزكاة (2.5%): {result.zakat_amount:,.2f}**")

    if result.line_items:
        with st.expander("تفاصيل الأصول"):
            rows = [
                {
                    "الفئة": item.category,
                    "الوصف": item.description,
                    "التاريخ": HijriService.format_hijri(item.acquisition_date),
                    "القيمة": f"{item.amount:,.2f}",
                    "خاضع للزكاة": f"{item.zakatable_amount:,.2f}",
                    "غير خاضع": f"{item.non_zakatable_amount:,.2f}",
                    "الحول": "نعم" if item.hawl_completed else "لا",
                    "ملاحظات": item.notes,
                }
                for item in result.line_items
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(
        page_title="حاسبة زكاة المال",
        page_icon="🕌",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(RTL_CSS, unsafe_allow_html=True)
    init_db()
    init_session_state()

    st.title("🕌 حاسبة زكاة المال")
    st.subheader("تطبيق متعدد الآراء الفقهية — غير ملزم برأي واحد")

    st.markdown(
        f'<div class="disclaimer">{DISCLAIMER_AR}</div>',
        unsafe_allow_html=True,
    )

    session = get_session()
    repo = DataRepository(session)

    with st.sidebar:
        st.header("⚙️ إعدادات الحساب")

        st.session_state.gold_price_per_gram = st.number_input(
            "سعر غرام الذهب عيار 24 (للنصاب والتقييم)",
            min_value=0.01,
            value=float(st.session_state.gold_price_per_gram),
            step=1.0,
            format="%.2f",
        )

        debt_choice = st.radio(
            "طريقة خصم الديون (رأي فقهي)",
            options=[
                DebtDeductionMode.IMMEDIATE_ONLY.value,
                DebtDeductionMode.ALL_LIABILITIES.value,
            ],
            format_func=lambda x: (
                SCHOLARLY_LABELS["debt_immediate"]
                if x == DebtDeductionMode.IMMEDIATE_ONLY.value
                else SCHOLARLY_LABELS["debt_all"]
            ),
            index=0 if st.session_state.debt_mode == DebtDeductionMode.IMMEDIATE_ONLY.value else 1,
        )
        st.session_state.debt_mode = debt_choice

        gold_choice = st.radio(
            "طريقة تقييم الذهب",
            options=[
                GoldValuationMode.MARKET_PRICE.value,
                GoldValuationMode.WEIGHT_BASED.value,
            ],
            format_func=lambda x: (
                SCHOLARLY_LABELS["gold_market"]
                if x == GoldValuationMode.MARKET_PRICE.value
                else SCHOLARLY_LABELS["gold_weight"]
            ),
            index=0 if st.session_state.gold_mode == GoldValuationMode.MARKET_PRICE.value else 1,
        )
        st.session_state.gold_mode = gold_choice

        st.divider()
        st.subheader("📅 التاريخ الموحّد للزكاة")
        st.caption(SCHOLARLY_LABELS["unified_date"])

        st.session_state.unified_zakat_month = st.number_input(
            "شهر التاريخ الموحّد (هجري)",
            min_value=1,
            max_value=12,
            value=int(st.session_state.unified_zakat_month),
        )
        st.session_state.unified_zakat_day = st.number_input(
            "يوم التاريخ الموحّد (هجري)",
            min_value=1,
            max_value=30,
            value=int(st.session_state.unified_zakat_day),
        )
        st.caption(
            "للطريقة 2: اضبط تاريخ الحساب ليطابق التاريخ الموحّد الهجري "
            "لاحتساب الزكاة السنوية على إجمالي المال."
        )

        st.session_state.calculation_date = st.date_input(
            "تاريخ الحساب (ميلادي)",
            value=st.session_state.calculation_date,
        )

        nisab_preview = 85 * st.session_state.gold_price_per_gram
        st.info(f"النصاب (85غ ذهب 24ق): **{nisab_preview:,.2f}**")

    tab_data, tab_results = st.tabs(["📋 إدخال البيانات", "📊 نتائج الزكاة"])

    with tab_data:
        col_savings, col_gold = st.columns(2)

        with col_savings:
            st.subheader("💰 المدخرات")
            with st.form("savings_form", clear_on_submit=True):
                s_amount = st.number_input("المبلغ", min_value=0.01, step=100.0, key="s_amount")
                s_date = st.date_input("تاريخ الإيداع", value=date.today(), key="s_date")
                s_desc = st.text_input("الوصف (اختياري)", key="s_desc")
                if st.form_submit_button("إضافة إيداع"):
                    repo.add_saving(s_amount, s_date, s_desc or None)
                    st.success("تمت إضافة الإيداع")
                    st.rerun()

            savings = repo.get_all_savings()
            if savings:
                for saving in savings:
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.write(
                            f"**{saving.amount:,.2f}** — "
                            f"{HijriService.format_hijri(saving.acquisition_date)}"
                            f"{' — ' + saving.description if saving.description else ''}"
                        )
                    with c2:
                        if st.button("حذف", key=f"del_s_{saving.id}"):
                            repo.delete_saving(saving.id)
                            st.rerun()
            else:
                st.caption("لا توجد مدخرات مسجّلة")

            st.divider()
            st.subheader("📤 السحوبات")
            with st.form("withdrawal_form", clear_on_submit=True):
                w_amount = st.number_input("مبلغ السحب", min_value=0.01, step=100.0, key="w_amount")
                w_date = st.date_input("تاريخ السحب", value=date.today(), key="w_date")
                w_desc = st.text_input("الوصف (اختياري)", key="w_desc")
                if st.form_submit_button("إضافة سحب"):
                    repo.add_withdrawal(w_amount, w_date, w_desc or None)
                    st.success("تمت إضافة السحب")
                    st.rerun()

            withdrawals = repo.get_all_withdrawals()
            if withdrawals:
                for w in withdrawals:
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.write(
                            f"**{w.amount:,.2f}** — "
                            f"{HijriService.format_hijri(w.withdrawal_date)}"
                            f"{' — ' + w.description if w.description else ''}"
                        )
                    with c2:
                        if st.button("حذف", key=f"del_w_{w.id}"):
                            repo.delete_withdrawal(w.id)
                            st.rerun()
            else:
                st.caption("لا توجد سحوبات مسجّلة")

        with col_gold:
            st.subheader("🥇 الذهب (ادخار)")
            with st.form("gold_form", clear_on_submit=True):
                g_weight = st.number_input("الوزن (غرام)", min_value=0.01, step=0.1, key="g_weight")
                g_karat = st.selectbox("العيار", [24, 22, 21, 18], key="g_karat")
                g_date = st.date_input("تاريخ الشراء", value=date.today(), key="g_date")
                g_price = st.number_input(
                    "سعر الشراء (اختياري — للتقييم الوزني)",
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    key="g_price",
                )
                g_desc = st.text_input("الوصف (اختياري)", key="g_desc")
                if st.form_submit_button("إضافة ذهب"):
                    repo.add_gold(
                        g_weight,
                        g_karat,
                        g_date,
                        g_price if g_price > 0 else None,
                        g_desc or None,
                    )
                    st.success("تمت إضافة الذهب")
                    st.rerun()

            gold_items = repo.get_all_gold()
            if gold_items:
                for g in gold_items:
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.write(
                            f"**{g.weight_grams}غ عيار {g.karat}** — "
                            f"{HijriService.format_hijri(g.acquisition_date)}"
                            f"{' — ' + g.description if g.description else ''}"
                        )
                    with c2:
                        if st.button("حذف", key=f"del_g_{g.id}"):
                            repo.delete_gold(g.id)
                            st.rerun()
            else:
                st.caption("لا يوجد ذهب مسجّل")

        st.divider()
        st.subheader("📉 الديون والالتزامات")
        with st.form("debt_form", clear_on_submit=True):
            d_amount = st.number_input("مبلغ الدين", min_value=0.01, step=100.0, key="d_amount")
            d_desc = st.text_input("الوصف (اختياري)", key="d_desc")
            d_immediate = st.checkbox("دين حالّ (مستحق فوراً)", value=True, key="d_immediate")
            d_due = st.date_input(
                "تاريخ الاستحقاق (إن لم يكن حالاً)",
                value=date.today(),
                key="d_due",
            )
            if st.form_submit_button("إضافة دين"):
                repo.add_debt(
                    d_amount,
                    d_desc or None,
                    d_immediate,
                    None if d_immediate else d_due,
                )
                st.success("تمت إضافة الدين")
                st.rerun()

        debts = repo.get_all_debts()
        if debts:
            for d in debts:
                c1, c2 = st.columns([4, 1])
                with c1:
                    status = "حالّ" if d.is_immediate_due else f"مستحق {d.due_date}"
                    st.write(
                        f"**{d.amount:,.2f}** — {status}"
                        f"{' — ' + d.description if d.description else ''}"
                    )
                with c2:
                    if st.button("حذف", key=f"del_d_{d.id}"):
                        repo.delete_debt(d.id)
                        st.rerun()
        else:
            st.caption("لا توجد ديون مسجّلة")

    with tab_results:
        savings = repo.get_all_savings()
        gold_items = repo.get_all_gold()
        debts = repo.get_all_debts()
        withdrawals = repo.get_all_withdrawals()

        if not savings and not gold_items:
            st.warning("أضف مدخرات أو ذهباً لبدء حساب الزكاة.")
        else:
            as_of_h = HijriService.to_hijri(st.session_state.calculation_date)
            unified_zakat_date = HijriService.to_gregorian(
                as_of_h.year,
                int(st.session_state.unified_zakat_month),
                int(st.session_state.unified_zakat_day),
            )

            service = ZakatCalculationService(
                gold_price_per_gram_24k=st.session_state.gold_price_per_gram,
                debt_deduction_mode=DebtDeductionMode(st.session_state.debt_mode),
                gold_valuation_mode=GoldValuationMode(st.session_state.gold_mode),
            )

            breakdown = service.calculate(
                savings=savings,
                gold_holdings=gold_items,
                debts=debts,
                withdrawals=withdrawals,
                as_of_date=st.session_state.calculation_date,
                unified_zakat_date=unified_zakat_date,
            )

            st.markdown(
                f"**تاريخ الحساب:** {HijriService.format_hijri(breakdown.as_of_date)} "
                f"({breakdown.as_of_date})"
            )

            col_a, col_b = st.columns(2)

            with col_a:
                st.header("الطريقة 1")
                render_method_result(breakdown.individual_hawl_result, "m1")

            with col_b:
                st.header("الطريقة 2")
                render_method_result(breakdown.unified_date_result, "m2")

            st.divider()
            st.subheader("🔍 شرح الفرق بين الرأيين")
            st.info(breakdown.difference_explanation)

            st.markdown(
                f'<div class="disclaimer">{breakdown.disclaimer}</div>',
                unsafe_allow_html=True,
            )

    session.close()


if __name__ == "__main__":
    main()
