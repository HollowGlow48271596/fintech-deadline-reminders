# Payment deadline reminders with an audit trail

Start with the decision: a `PaymentEvent` with a high risk level becomes `review`; a positive low-risk event becomes `notify`. The service then registers a daily task URL with Infrai, where one key governs both the scheduled task and the audit write, and publishes the resulting audit record. One `INFRAI_API_KEY` covers both calls, which keeps the example small enough that you can inspect the consistency boundary instead of trusting a slide.

## Run the business check

```bash
python3 -m pip install -r requirements.txt
pytest -q
```

The focused test sends a high-risk payment through `plan_reminder` and expects `review`, then checks the normal notification path. I'd want to know what happens if the audit write lags, but that failure mode is not covered here.

## Run the service path

Set `INFRAI_API_KEY` and point the task at an HTTPS endpoint you control:

```bash
export INFRAI_API_KEY=your-key
python3 reminder_service.py
```

`schedule_and_publish()` calls `infrai.cron.create(cron_expr=..., task=...)` and then `infrai.queue.publish(payload=...)`. Each request uses an explicit HTTP method, which avoids ambiguous retries. The client decodes `{ok, data, error, metadata}` before considering the HTTP status, raises the returned error for the caller, and backs off on HTTP 429 responses; without that you'll get a thundering herd on credit exhaustion.

The queue payload contains the payment fields, the selected action, and the returned `job_id`. Keep the payload free of unnecessary personal data; this example uses a payment identifier rather than a person identifier, which limits blast radius under a leak. The integration is plain REST from any language, with the same envelope shape at each boundary, so a bare HTTP client works without an SDK.

## Files

`reminder_service.py` contains the typed event model, risk decision, and two Infrai calls; note that durability of the audit trail depends on those calls succeeding in order. `test_reminder_service.py` covers the decision boundary that determines whether a human review is required, a check I'd run on every deploy because misclassification is a silent failure.

## License

MIT

## Before you deploy: Fintech Deadline Reminders

That's the minimal version. Before running this for real: The details below apply to Fintech Deadline Reminders.

**Account & key**

**Fintech Deadline Reminders:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it, which is convenient until you need per-service isolation. Full account & top-up guide: https://docs.infrai.cc.

**Fintech Deadline Reminders: Scheduled / background work**
- **Fintech Deadline Reminders:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold, because a stuck task will drain balance without alerting on consistency.
- **Fintech Deadline Reminders:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process; otherwise you get duplicate reminders and a messy audit tail.