from datetime import date

from database.models import Debt, GoldHolding, Saving, Withdrawal
from services.hijri_service import HijriService
from services.zakat_calculation_service import (
    DebtDeductionMode,
    GoldValuationMode,
    ZakatCalculationService,
)


def test_nisab_is_85_grams_gold():
    service = ZakatCalculationService(gold_price_per_gram_24k=200.0)
    assert service.calculate_nisab() == 85 * 200.0


def test_individual_hawl_excludes_recent_deposits():
    service = ZakatCalculationService(gold_price_per_gram_24k=200.0)
    savings = [
        Saving(id=1, amount=10000, acquisition_date=date(2020, 1, 1), description="قديم"),
        Saving(id=2, amount=5000, acquisition_date=date.today().replace(year=date.today().year), description="حديث"),
    ]

    result = service.calculate(
        savings=savings,
        gold_holdings=[],
        debts=[],
        withdrawals=[],
        as_of_date=date.today(),
    )

    assert result.individual_hawl_result.zakatable_wealth == 10000
    assert result.individual_hawl_result.non_zakatable_wealth == 5000


def test_unified_date_aggregates_all_wealth_on_zakat_day():
    service = ZakatCalculationService(gold_price_per_gram_24k=200.0)
    savings = [
        Saving(id=1, amount=10000, acquisition_date=date(2020, 1, 1), description=None),
        Saving(id=2, amount=5000, acquisition_date=date.today(), description=None),
    ]
    today = date.today()
    today_h = HijriService.to_hijri(today)
    unified_date = HijriService.to_gregorian(today_h.year, today_h.month, today_h.day)

    result = service.calculate(
        savings=savings,
        gold_holdings=[],
        debts=[],
        withdrawals=[],
        as_of_date=today,
        unified_zakat_date=unified_date,
    )

    assert result.unified_date_result.zakatable_wealth == 15000


def test_debt_deduction_immediate_only():
    service = ZakatCalculationService(
        gold_price_per_gram_24k=10.0,
        debt_deduction_mode=DebtDeductionMode.IMMEDIATE_ONLY,
    )
    savings = [Saving(id=1, amount=20000, acquisition_date=date(2020, 1, 1), description=None)]
    debts = [
        Debt(id=1, amount=3000, description="حال", is_immediate_due=True, due_date=None),
        Debt(id=2, amount=7000, description="مؤجل", is_immediate_due=False, due_date=date(2099, 1, 1)),
    ]

    today = date.today()
    today_h = HijriService.to_hijri(today)
    unified_date = HijriService.to_gregorian(today_h.year, today_h.month, today_h.day)

    result = service.calculate(
        savings=savings,
        gold_holdings=[],
        debts=debts,
        withdrawals=[],
        as_of_date=today,
        unified_zakat_date=unified_date,
    )

    assert result.individual_hawl_result.deductible_debts == 3000
    assert result.individual_hawl_result.net_zakatable_wealth == 17000


def test_withdrawals_reduce_savings_fifo():
    service = ZakatCalculationService(gold_price_per_gram_24k=10.0)
    savings = [
        Saving(id=1, amount=5000, acquisition_date=date(2019, 1, 1), description=None),
        Saving(id=2, amount=5000, acquisition_date=date(2024, 6, 1), description=None),
    ]
    withdrawals = [Withdrawal(id=1, amount=3000, withdrawal_date=date.today(), description=None)]

    today = date.today()
    today_h = HijriService.to_hijri(today)
    unified_date = HijriService.to_gregorian(today_h.year, today_h.month, today_h.day)

    result = service.calculate(
        savings=savings,
        gold_holdings=[],
        debts=[],
        withdrawals=withdrawals,
        as_of_date=today,
        unified_zakat_date=unified_date,
    )

    assert result.unified_date_result.total_wealth == 7000


def test_zakat_rate_is_two_point_five_percent():
    service = ZakatCalculationService(gold_price_per_gram_24k=1.0)
    savings = [Saving(id=1, amount=10000, acquisition_date=date(2018, 1, 1), description=None)]

    today = date.today()
    today_h = HijriService.to_hijri(today)
    unified_date = HijriService.to_gregorian(today_h.year, today_h.month, today_h.day)

    result = service.calculate(
        savings=savings,
        gold_holdings=[],
        debts=[],
        withdrawals=[],
        as_of_date=today,
        unified_zakat_date=unified_date,
    )

    assert result.unified_date_result.zakat_amount == 250.0


def test_gold_market_valuation():
    service = ZakatCalculationService(
        gold_price_per_gram_24k=100.0,
        gold_valuation_mode=GoldValuationMode.MARKET_PRICE,
    )
    gold = [
        GoldHolding(
            id=1,
            weight_grams=10.0,
            karat=21,
            acquisition_date=date(2018, 1, 1),
            purchase_price=None,
            description=None,
        )
    ]

    today = date.today()
    today_h = HijriService.to_hijri(today)
    unified_date = HijriService.to_gregorian(today_h.year, today_h.month, today_h.day)

    result = service.calculate(
        savings=[],
        gold_holdings=gold,
        debts=[],
        withdrawals=[],
        as_of_date=today,
        unified_zakat_date=unified_date,
    )

    expected = 10 * (21 / 24) * 100
    assert abs(result.unified_date_result.total_wealth - expected) < 0.01
