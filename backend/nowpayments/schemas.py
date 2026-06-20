from ninja import Schema


class CustodyDepositCreateSchema(Schema):
    currency: str
    amount: float | str


class CustodyAccountSchema(Schema):
    sub_partner_id: str
    name: str


class CustodyBalanceSchema(Schema):
    account: CustodyAccountSchema
    provider_balance: dict


class CustodyDepositSchema(Schema):
    id: str
    sub_partner_id: str
    currency: str
    amount: str
    provider_payment_id: str
    pay_address: str
    pay_amount: str | None
    payment_status: str
    provider_payload: dict


class NowPaymentsIPNSchema(Schema):
    payment_id: int | str | None = None
    payment_status: str | None = None
    pay_address: str | None = None
    price_amount: float | str | None = None
    price_currency: str | None = None
    pay_amount: float | str | None = None
    actually_paid: float | str | None = None
    pay_currency: str | None = None
    order_id: str | None = None
    order_description: str | None = None
    purchase_id: str | None = None
    outcome_amount: float | str | None = None
    outcome_currency: str | None = None


class NowPaymentsDiagnosticSchema(Schema):
    configured: bool
    status: dict
    currencies: dict
    balance: dict
