import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("ZAKAT_DB_PATH", BASE_DIR / "zakat.db"))
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

ZAKAT_RATE = 0.025
NISAB_GOLD_GRAMS_24K = 85

SCHOLARLY_LABELS = {
    "individual_hawl": "الرأي الفقهي الكلاسيكي — حول مستقل لكل مال",
    "unified_date": "الرأي الفقهي المعاصر — تاريخ زكاة موحّد",
    "debt_immediate": "رأي فقهي: خصم الديون الحالة فقط",
    "debt_all": "رأي فقهي: خصم جميع الالتزامات",
    "gold_market": "التقييم بسعر السوق الحالي",
    "gold_weight": "التقييم بالوزن (سعر الشراء أو البديل الوزني)",
}

DISCLAIMER_AR = (
    "تنبيه شرعي: النتائج المعروضة مبنية على آراء فقهية معتبرة وليست حكماً مطلقاً. "
    "يُنصح باستشارة عالم مختص للحالات الخاصة."
)
