from dataclasses import dataclass


@dataclass
class GoldValuation:
    weight_grams: float
    karat: int
    purity_factor: float
    pure_gold_grams: float
    value: float
    method_label: str


class GoldService:
    """Gold valuation supporting market price and weight-based alternatives."""

    @staticmethod
    def purity_factor(karat: int) -> float:
        return karat / 24.0

    @staticmethod
    def value_by_market(
        weight_grams: float,
        karat: int,
        market_price_per_gram_24k: float,
    ) -> GoldValuation:
        purity = GoldService.purity_factor(karat)
        pure_grams = weight_grams * purity
        value = pure_grams * market_price_per_gram_24k
        return GoldValuation(
            weight_grams=weight_grams,
            karat=karat,
            purity_factor=purity,
            pure_gold_grams=pure_grams,
            value=value,
            method_label="التقييم بسعر السوق الحالي للذهب عيار 24",
        )

    @staticmethod
    def value_by_weight_alternative(
        weight_grams: float,
        karat: int,
        purchase_price: float | None,
        market_price_per_gram_24k: float,
    ) -> GoldValuation:
        """
        Weight-based alternative: uses purchase price when recorded,
        otherwise falls back to pure gold weight × market rate.
        """
        purity = GoldService.purity_factor(karat)
        pure_grams = weight_grams * purity

        if purchase_price is not None and purchase_price > 0:
            value = purchase_price
            method_label = "التقييم بسعر الشراء المسجّل (بديل وزني)"
        else:
            value = pure_grams * market_price_per_gram_24k
            method_label = "التقييم بالوزن الصافي × سعر الذهب (بديل وزني)"

        return GoldValuation(
            weight_grams=weight_grams,
            karat=karat,
            purity_factor=purity,
            pure_gold_grams=pure_grams,
            value=value,
            method_label=method_label,
        )
