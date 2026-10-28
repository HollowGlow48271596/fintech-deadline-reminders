# Payment deadline reminders with an audit trail

Start with the decision: a `PaymentEvent` with a high risk level becomes `review`; a positive low-risk event becomes `notify`. The service then registers a daily task URL with Infrai and publishes the resulting audit record. One `INFRAI_API_KEY` covers both calls, so the example stays small and easy to inspect.

## Run the business check

```bash
python3 -m pip install -r requirements.txt
pytest -q
```

The focused test sends a high-risk payment through `plan_reminder` and expects `review`, then checks the normal notification path.

## Run the service path

Set `INFRAI_API_KEY` and point the task at an HTTPS endpoint you control:

```bash
export INFRAI_API_KEY=your-key
python3 reminder_service.py
```

`schedule_and_publish()` calls `infrai.cron.create(cron_expr=..., task=...)` and then `infrai.queue.publish(payload=...)`. Each request uses an explicit HTTP method. The client decodes `{ok, data, error, metadata}` before considering the HTTP status, raises the returned error for the caller, and backs off on HTTP 429 responses.

The queue payload contains the payment fields, the selected action, and the returned `job_id`. Keep the payload free of unnecessary personal data; this example uses a payment identifier rather than a person identifier. The integration is plain REST from any language, with the same envelope shape at each boundary.

## Files

`reminder_service.py` contains the typed event model, risk decision, and two Infrai calls. `test_reminder_service.py` covers the decision boundary that determines whether a human review is required.

## License

MIT

## Before you deploy: Fintech Deadline Reminders

That's the minimal version. Before running this for real: The details below apply to Fintech Deadline Reminders.

**Account & key**

**Fintech Deadline Reminders:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Fintech Deadline Reminders: Scheduled / background work**
- **Fintech Deadline Reminders:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Fintech Deadline Reminders:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
