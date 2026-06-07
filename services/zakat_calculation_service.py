from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from config import NISAB_GOLD_GRAMS_24K, SCHOLARLY_LABELS, ZAKAT_RATE
from database.models import Debt, GoldHolding, Saving, Withdrawal
from services.gold_service import GoldService
from services.hijri_service import HijriService


class DebtDeductionMode(str, Enum):
    IMMEDIATE_ONLY = "immediate_only"
    ALL_LIABILITIES = "all_liabilities"


class GoldValuationMode(str, Enum):
    MARKET_PRICE = "market_price"
    WEIGHT_BASED = "weight_based"


@dataclass
class AssetLineItem:
    category: str
    description: str
    amount: float
    acquisition_date: date
    hawl_completed: bool
    zakatable_amount: float
    non_zakatable_amount: float
    notes: str = ""


@dataclass
class MethodResult:
    scholarly_opinion_label: str
    scholarly_opinion_key: str
    total_wealth: float
    zakatable_wealth: float
    non_zakatable_wealth: float
    deductible_debts: float
    net_zakatable_wealth: float
    nisab_threshold: float
    meets_nisab: bool
    zakat_amount: float
    line_items: list[AssetLineItem] = field(default_factory=list)
    explanation: str = ""


@dataclass
class CalculationBreakdown:
    as_of_date: date
    nisab_threshold: float
    nisab_gold_grams: float
    gold_price_per_gram_24k: float
    debt_deduction_mode: DebtDeductionMode
    gold_valuation_mode: GoldValuationMode
    individual_hawl_result: MethodResult
    unified_date_result: MethodResult
    difference_explanation: str
    disclaimer: str


class ZakatCalculationService:
    """
    Sharia-aware Zakat calculation engine implementing multiple scholarly opinions.
    Results are labeled as opinions, not absolute rulings.
    """

    def __init__(
        self,
        gold_price_per_gram_24k: float,
        debt_deduction_mode: DebtDeductionMode = DebtDeductionMode.IMMEDIATE_ONLY,
        gold_valuation_mode: GoldValuationMode = GoldValuationMode.MARKET_PRICE,
    ):
        self.gold_price_per_gram_24k = gold_price_per_gram_24k
        self.debt_deduction_mode = debt_deduction_mode
        self.gold_valuation_mode = gold_valuation_mode
        self.hijri = HijriService()
        self.gold = GoldService()

    def calculate_nisab(self) -> float:
        return NISAB_GOLD_GRAMS_24K * self.gold_price_per_gram_24k

    def calculate(
        self,
        savings: list[Saving],
        gold_holdings: list[GoldHolding],
        debts: list[Debt],
        withdrawals: list[Withdrawal],
        as_of_date: date,
        unified_zakat_date: date | None = None,
    ) -> CalculationBreakdown:
        nisab = self.calculate_nisab()
        deductible_debts = self._calculate_deductible_debts(debts, as_of_date)

        individual = self._calculate_individual_hawl(
            savings, gold_holdings, withdrawals, as_of_date, nisab, deductible_debts
        )

        unified = self._calculate_unified_date(
            savings,
            gold_holdings,
            withdrawals,
            as_of_date,
            unified_zakat_date,
            nisab,
            deductible_debts,
        )

        difference = self._explain_difference(individual, unified)

        return CalculationBreakdown(
            as_of_date=as_of_date,
            nisab_threshold=nisab,
            nisab_gold_grams=NISAB_GOLD_GRAMS_24K,
            gold_price_per_gram_24k=self.gold_price_per_gram_24k,
            debt_deduction_mode=self.debt_deduction_mode,
            gold_valuation_mode=self.gold_valuation_mode,
            individual_hawl_result=individual,
            unified_date_result=unified,
            difference_explanation=difference,
            disclaimer=(
                "النتائج مبنية على آراء فقهية معتبرة وليست حكماً شرعياً مطلقاً. "
                "يُنصح بمراجعة أهل العلم للحالات الخاصة."
            ),
        )

    def _calculate_deductible_debts(self, debts: list[Debt], as_of_date: date) -> float:
        if not debts:
            return 0.0

        if self.debt_deduction_mode == DebtDeductionMode.ALL_LIABILITIES:
            return sum(d.amount for d in debts)

        total = 0.0
        for debt in debts:
            if debt.is_immediate_due:
                total += debt.amount
            elif debt.due_date and debt.due_date <= as_of_date:
                total += debt.amount
        return total

    def _apply_withdrawals_to_savings(
        self, savings: list[Saving], withdrawals: list[Withdrawal]
    ) -> list[tuple[Saving, float]]:
        """
        FIFO withdrawal application (رأي عملي شائع):
        withdrawals reduce oldest deposits first.
        """
        sorted_savings = sorted(savings, key=lambda s: s.acquisition_date)
        remaining = {s.id: s.amount for s in sorted_savings}
        total_withdrawn = sum(w.amount for w in withdrawals)

        for saving in sorted_savings:
            if total_withdrawn <= 0:
                break
            deduct = min(remaining[saving.id], total_withdrawn)
            remaining[saving.id] -= deduct
            total_withdrawn -= deduct

        return [(s, remaining[s.id]) for s in sorted_savings if remaining[s.id] > 0]

    def _value_gold(self, holding: GoldHolding) -> float:
        if self.gold_valuation_mode == GoldValuationMode.MARKET_PRICE:
            return self.gold.value_by_market(
                holding.weight_grams, holding.karat, self.gold_price_per_gram_24k
            ).value
        return self.gold.value_by_weight_alternative(
            holding.weight_grams,
            holding.karat,
            holding.purchase_price,
            self.gold_price_per_gram_24k,
        ).value

    def _calculate_individual_hawl(
        self,
        savings: list[Saving],
        gold_holdings: list[GoldHolding],
        withdrawals: list[Withdrawal],
        as_of_date: date,
        nisab: float,
        deductible_debts: float,
    ) -> MethodResult:
        line_items: list[AssetLineItem] = []
        zakatable = 0.0
        non_zakatable = 0.0
        total_wealth = 0.0

        adjusted_savings = self._apply_withdrawals_to_savings(savings, withdrawals)

        for saving, remaining_amount in adjusted_savings:
            hawl_done = self.hijri.has_completed_hawl(saving.acquisition_date, as_of_date)
            z_amount = remaining_amount if hawl_done else 0.0
            nz_amount = 0.0 if hawl_done else remaining_amount

            zakatable += z_amount
            non_zakatable += nz_amount
            total_wealth += remaining_amount

            notes = (
                "أتم الحول الهجري"
                if hawl_done
                else f"لم يكتمل الحول — يكتمل في {self.hijri.format_hijri(self.hijri.next_hawl_date(saving.acquisition_date))}"
            )

            line_items.append(
                AssetLineItem(
                    category="مدخرات",
                    description=saving.description or f"إيداع #{saving.id}",
                    amount=remaining_amount,
                    acquisition_date=saving.acquisition_date,
                    hawl_completed=hawl_done,
                    zakatable_amount=z_amount,
                    non_zakatable_amount=nz_amount,
                    notes=notes,
                )
            )

        for holding in gold_holdings:
            value = self._value_gold(holding)
            hawl_done = self.hijri.has_completed_hawl(
                holding.acquisition_date, as_of_date
            )
            z_amount = value if hawl_done else 0.0
            nz_amount = 0.0 if hawl_done else value

            zakatable += z_amount
            non_zakatable += nz_amount
            total_wealth += value

            notes = (
                "أتم الحول الهجري"
                if hawl_done
                else f"لم يكتمل الحول — يكتمل في {self.hijri.format_hijri(self.hijri.next_hawl_date(holding.acquisition_date))}"
            )

            line_items.append(
                AssetLineItem(
                    category="ذهب ادخار",
                    description=holding.description
                    or f"ذهب {holding.weight_grams}غ عيار {holding.karat}",
                    amount=value,
                    acquisition_date=holding.acquisition_date,
                    hawl_completed=hawl_done,
                    zakatable_amount=z_amount,
                    non_zakatable_amount=nz_amount,
                    notes=notes,
                )
            )

        net_zakatable = max(zakatable - deductible_debts, 0.0)
        meets_nisab = net_zakatable >= nisab
        zakat = net_zakatable * ZAKAT_RATE if meets_nisab else 0.0

        debt_label = (
            SCHOLARLY_LABELS["debt_immediate"]
            if self.debt_deduction_mode == DebtDeductionMode.IMMEDIATE_ONLY
            else SCHOLARLY_LABELS["debt_all"]
        )

        return MethodResult(
            scholarly_opinion_label=SCHOLARLY_LABELS["individual_hawl"],
            scholarly_opinion_key="individual_hawl",
            total_wealth=total_wealth,
            zakatable_wealth=zakatable,
            non_zakatable_wealth=non_zakatable,
            deductible_debts=deductible_debts,
            net_zakatable_wealth=net_zakatable,
            nisab_threshold=nisab,
            meets_nisab=meets_nisab,
            zakat_amount=zakat,
            line_items=line_items,
            explanation=(
                f"وفق الرأي الفقهي الكلاسيكي: تُزكّى كل مادة مالٍ على حدة بعد اكتمال حولها الهجري. "
                f"المدخرات التي لم يمضَ عليها سنة هجرية كاملة غير خاضعة للزكاة. "
                f"خصم الديون: {debt_label}. "
                f"نسبة الزكاة: {ZAKAT_RATE * 100}%."
            ),
        )

    def _calculate_unified_date(
        self,
        savings: list[Saving],
        gold_holdings: list[GoldHolding],
        withdrawals: list[Withdrawal],
        as_of_date: date,
        unified_zakat_date: date | None,
        nisab: float,
        deductible_debts: float,
    ) -> MethodResult:
        line_items: list[AssetLineItem] = []
        total_wealth = 0.0

        adjusted_savings = self._apply_withdrawals_to_savings(savings, withdrawals)

        on_unified_date = self._is_on_unified_zakat_date(as_of_date, unified_zakat_date)

        for saving, remaining_amount in adjusted_savings:
            total_wealth += remaining_amount
            eligible = on_unified_date

            line_items.append(
                AssetLineItem(
                    category="مدخرات",
                    description=saving.description or f"إيداع #{saving.id}",
                    amount=remaining_amount,
                    acquisition_date=saving.acquisition_date,
                    hawl_completed=eligible,
                    zakatable_amount=remaining_amount if eligible else 0.0,
                    non_zakatable_amount=0.0 if eligible else remaining_amount,
                    notes=(
                        "مشمول بنظام التاريخ الموحّد — يُجمع مع كامل المال"
                        if on_unified_date
                        else "يُزكّى عند حلول التاريخ الموحّد السنوي"
                    ),
                )
            )

        for holding in gold_holdings:
            value = self._value_gold(holding)
            total_wealth += value
            eligible = on_unified_date

            line_items.append(
                AssetLineItem(
                    category="ذهب ادخار",
                    description=holding.description
                    or f"ذهب {holding.weight_grams}غ عيار {holding.karat}",
                    amount=value,
                    acquisition_date=holding.acquisition_date,
                    hawl_completed=eligible,
                    zakatable_amount=value if eligible else 0.0,
                    non_zakatable_amount=0.0 if eligible else value,
                    notes=(
                        "مشمول بنظام التاريخ الموحّد — يُجمع مع كامل المال"
                        if on_unified_date
                        else "يُزكّى عند حلول التاريخ الموحّد السنوي"
                    ),
                )
            )

        zakatable = sum(item.zakatable_amount for item in line_items)
        non_zakatable = sum(item.non_zakatable_amount for item in line_items)
        net_zakatable = max(zakatable - deductible_debts, 0.0)
        meets_nisab = net_zakatable >= nisab
        zakat = net_zakatable * ZAKAT_RATE if meets_nisab else 0.0

        date_note = (
            f"تاريخ الزكاة الموحّد: {self.hijri.format_hijri(unified_zakat_date)}"
            if unified_zakat_date
            else "لم يُحدد تاريخ زكاة موحّد — يُحسب فقط ما أتم الحول"
        )

        debt_label = (
            SCHOLARLY_LABELS["debt_immediate"]
            if self.debt_deduction_mode == DebtDeductionMode.IMMEDIATE_ONLY
            else SCHOLARLY_LABELS["debt_all"]
        )

        return MethodResult(
            scholarly_opinion_label=SCHOLARLY_LABELS["unified_date"],
            scholarly_opinion_key="unified_date",
            total_wealth=total_wealth,
            zakatable_wealth=zakatable,
            non_zakatable_wealth=non_zakatable,
            deductible_debts=deductible_debts,
            net_zakatable_wealth=net_zakatable,
            nisab_threshold=nisab,
            meets_nisab=meets_nisab,
            zakat_amount=zakat,
            line_items=line_items,
            explanation=(
                f"وفق الرأي الفقهي المعاصر: يُحدد تاريخ سنوي موحّد للزكاة وتُجمع الأموال المؤهلة فيه. "
                f"{date_note}. خصم الديون: {debt_label}. نسبة الزكاة: {ZAKAT_RATE * 100}%."
            ),
        )

    def _is_on_unified_zakat_date(
        self, as_of_date: date, unified_zakat_date: date | None
    ) -> bool:
        if unified_zakat_date is None:
            return False

        as_of_h = self.hijri.to_hijri(as_of_date)
        unified_h = self.hijri.to_hijri(unified_zakat_date)

        return as_of_h.month == unified_h.month and as_of_h.day == unified_h.day

    def _explain_difference(
        self, individual: MethodResult, unified: MethodResult
    ) -> str:
        diff = unified.zakat_amount - individual.zakat_amount

        if abs(diff) < 0.01:
            return (
                "الفرق بين الرأيين طفيف أو معدوم في هذه الحالة. "
                "قد يحدث اختلاف أكبر عند وجود إيداعات حديثة لم تكتمل حولها "
                "مع استخدام نظام التاريخ الموحّد."
            )

        direction = "أعلى" if diff > 0 else "أقل"
        return (
            f"الفرق في مبلغ الزكاة: {abs(diff):,.2f} ({direction} في الرأي المعاصر). "
            f"السبب: الرأي الكلاسيكي يزكّي فقط المال الذي أتم حوله الهجري ({individual.zakatable_wealth:,.2f})، "
            f"بينما الرأي المعاصر يزكّي {unified.zakatable_wealth:,.2f} عند تطبيق نظام التاريخ الموحّد. "
            f"هذا الاختلاف طبيعي بين الآراء الفقهية وليس خطأً في الحساب."
        )
