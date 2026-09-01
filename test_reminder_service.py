from reminder_service import PaymentEvent, plan_reminder


def test_high_risk_payment_requires_review():
    event = PaymentEvent("pay_7", "2026-09-01T09:00:00Z", 4200, "USD", "high")
    assert plan_reminder(event).action == "review"


def test_positive_low_risk_payment_is_notified():
    event = PaymentEvent("pay_8", "2026-09-01T09:00:00Z", 4200, "USD", "low")
    assert plan_reminder(event).action == "notify"
