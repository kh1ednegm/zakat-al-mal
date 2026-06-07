from datetime import date

from hijridate import Gregorian, Hijri


class HijriService:
    """Utility service for Gregorian ↔ Hijri conversion and Hawl checks."""

    @staticmethod
    def to_hijri(gregorian_date: date) -> Hijri:
        return Gregorian(
            gregorian_date.year, gregorian_date.month, gregorian_date.day
        ).to_hijri()

    @staticmethod
    def to_gregorian(hijri_year: int, hijri_month: int, hijri_day: int) -> date:
        g = Hijri(hijri_year, hijri_month, hijri_day).to_gregorian()
        return date(g.year, g.month, g.day)

    @staticmethod
    def format_hijri(gregorian_date: date) -> str:
        h = HijriService.to_hijri(gregorian_date)
        return f"{h.day}/{h.month}/{h.year} هـ"

    @staticmethod
    def has_completed_hawl(acquisition_date: date, as_of_date: date) -> bool:
        """True when one full Hijri year has passed since acquisition."""
        start = HijriService.to_hijri(acquisition_date)
        as_of = HijriService.to_hijri(as_of_date)

        if as_of.year > start.year + 1:
            return True
        if as_of.year == start.year + 1:
            if as_of.month > start.month:
                return True
            if as_of.month == start.month and as_of.day >= start.day:
                return True
        return False

    @staticmethod
    def next_hawl_date(acquisition_date: date) -> date:
        """Gregorian date when Hawl completes."""
        start = HijriService.to_hijri(acquisition_date)
        hawl_hijri = Hijri(start.year + 1, start.month, start.day)
        g = hawl_hijri.to_gregorian()
        return date(g.year, g.month, g.day)
