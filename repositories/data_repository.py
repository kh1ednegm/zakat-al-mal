from datetime import date

from sqlalchemy.orm import Session

from database.models import Debt, GoldHolding, Saving, Withdrawal


class DataRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all_savings(self) -> list[Saving]:
        return self.session.query(Saving).order_by(Saving.acquisition_date).all()

    def get_all_gold(self) -> list[GoldHolding]:
        return self.session.query(GoldHolding).order_by(GoldHolding.acquisition_date).all()

    def get_all_debts(self) -> list[Debt]:
        return self.session.query(Debt).all()

    def get_all_withdrawals(self) -> list[Withdrawal]:
        return self.session.query(Withdrawal).order_by(Withdrawal.withdrawal_date).all()

    def add_saving(self, amount: float, acquisition_date: date, description: str | None) -> Saving:
        saving = Saving(amount=amount, acquisition_date=acquisition_date, description=description)
        self.session.add(saving)
        self.session.commit()
        return saving

    def add_gold(
        self,
        weight_grams: float,
        karat: int,
        acquisition_date: date,
        purchase_price: float | None,
        description: str | None,
    ) -> GoldHolding:
        gold = GoldHolding(
            weight_grams=weight_grams,
            karat=karat,
            acquisition_date=acquisition_date,
            purchase_price=purchase_price,
            description=description,
        )
        self.session.add(gold)
        self.session.commit()
        return gold

    def add_debt(
        self,
        amount: float,
        description: str | None,
        is_immediate_due: bool,
        due_date: date | None,
    ) -> Debt:
        debt = Debt(
            amount=amount,
            description=description,
            is_immediate_due=is_immediate_due,
            due_date=due_date,
        )
        self.session.add(debt)
        self.session.commit()
        return debt

    def add_withdrawal(
        self, amount: float, withdrawal_date: date, description: str | None
    ) -> Withdrawal:
        withdrawal = Withdrawal(
            amount=amount,
            withdrawal_date=withdrawal_date,
            description=description,
        )
        self.session.add(withdrawal)
        self.session.commit()
        return withdrawal

    def delete_saving(self, saving_id: int) -> None:
        self.session.query(Saving).filter(Saving.id == saving_id).delete()
        self.session.commit()

    def delete_gold(self, gold_id: int) -> None:
        self.session.query(GoldHolding).filter(GoldHolding.id == gold_id).delete()
        self.session.commit()

    def delete_debt(self, debt_id: int) -> None:
        self.session.query(Debt).filter(Debt.id == debt_id).delete()
        self.session.commit()

    def delete_withdrawal(self, withdrawal_id: int) -> None:
        self.session.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).delete()
        self.session.commit()
