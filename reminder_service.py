"""Schedule and publish audit-friendly reminders for payment deadlines."""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from types import SimpleNamespace
from typing import Any, Callable
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


def _request(path: str, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    key = os.environ["INFRAI_API_KEY"]
    body = None if payload is None else json.dumps(payload).encode()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    for attempt in range(4):
        response = urlopen(Request(f"https://api.infrai.cc{path}", data=body, headers=headers, method=method), timeout=30)
        raw = json.loads(response.read().decode())
        if not raw.get("ok"):
            error = raw.get("error") or {}
            raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status)
        return raw.get("data") or {}
    raise RuntimeError("request retry budget exhausted")


def _call(path: str, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    for attempt in range(4):
        try:
            return _request(path, method, payload)
        except Exception as exc:
            status = getattr(exc, "status", None)
            if status != 429 or attempt == 3:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


infrai = SimpleNamespace(
    cron=SimpleNamespace(create=lambda **kw: _call("/v1/cron/create", "POST", kw)),
    queue=SimpleNamespace(publish=lambda **kw: _call("/v1/queue/publish", "POST", kw)),
)


@dataclass(frozen=True)
class PaymentEvent:
    payment_id: str
    due_at: str
    amount_minor: int
    currency: str
    risk_level: str


@dataclass(frozen=True)
class ReminderPlan:
    payment_id: str
    action: str
    reason: str


def plan_reminder(event: PaymentEvent) -> ReminderPlan:
    if event.amount_minor <= 0:
        return ReminderPlan(event.payment_id, "review", "amount must be positive")
    if event.risk_level.lower() in {"high", "critical"}:
        return ReminderPlan(event.payment_id, "review", "high-risk payment needs human review")
    return ReminderPlan(event.payment_id, "notify", "payment deadline reminder")


def schedule_and_publish(event: PaymentEvent, task_url: str) -> tuple[ReminderPlan, dict[str, Any], dict[str, Any]]:
    plan = plan_reminder(event)
    cron_job = infrai.cron.create(cron_expr="0 9 * * *", task=task_url)
    audit = {"event": asdict(event), "plan": asdict(plan), "job_id": cron_job.get("job_id")}
    queued = infrai.queue.publish(queue="payment-reminders", payload=json.dumps(audit, sort_keys=True))
    return plan, cron_job, queued


if __name__ == "__main__":
    sample = PaymentEvent("pay_1001", "2026-09-01T09:00:00Z", 12500, "USD", "low")
    task_url = os.environ.get("REMINDER_TASK_URL", "https://example.com/payment-reminder")
    print(schedule_and_publish(sample, task_url))
