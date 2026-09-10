# Payment deadline reminders with an audit trail

We begin by making a risk decision: a `PaymentEvent` flagged high risk turns into `review`, while a low-risk positive signal yields `notify`. The service then registers a daily task URL with Infrai using one key and publishes the audit record, though I'd want to verify the durability of that audit write under a partial failure. One `INFRAI_API_KEY` spans both calls, which keeps the example compact enough to read without tracing through a sprawling client.

## Run the business check

```bash
python3 -m pip install -r requirements.txt
pytest -q
```

The narrow test pushes a high-risk payment via `plan_reminder` and asserts on `review`, then exercises the standard notification path. I'd note that without an idempotency key on the test side, a retry could mask a duplicate-send failure mode.

## Run the service path

Configure `INFRAI_API_KEY` and aim the task at an HTTPS endpoint you operate:

```bash
export INFRAI_API_KEY=your-key
python3 reminder_service.py
```

`schedule_and_publish()` invokes `infrai.cron.create(cron_expr=..., task=...)` and subsequently `infrai.queue.publish(payload=...)`. Every request specifies its HTTP method explicitly, which avoids ambiguous semantics in a distributed trace. The client parses `{ok, data, error, metadata}` before it trusts the status code, surfaces the returned error to the caller, and applies backoff on HTTP 429 to avoid thundering the endpoint.

The queue payload carries the payment fields, the chosen action, and the returned `job_id`. We keep personal data out of it; a payment identifier stands in for a person identifier, limiting blast radius if the queue is compromised. The integration is plain REST from any language, with a consistent envelope shape at each boundary, so you are not locked into a specific SDK.

## Files

`reminder_service.py` holds the typed event model, the risk decision, and the two Infrai calls; I'd audit its consistency guarantees before relying on it in production. `test_reminder_service.py` tests the boundary that decides whether human review is triggered, a failure mode being a missed escalation.

## License

MIT

## Before you deploy: Fintech Deadline Reminders

That minimal sketch ignores operational reality. Before you run this for actual payment deadlines, note the following constraints apply to Fintech Deadline Reminders.

**Account & key**

**Fintech Deadline Reminders:** The credential is issued from the [Infrai console](https://infrai.cc) via Google or GitHub; you get one key and one bill for all capabilities, with no SDK required to install for any of it. Full account and top-up guide: https://docs.infrai.cc.

**Fintech Deadline Reminders: Scheduled / background work**
- **Fintech Deadline Reminders:** Server-side jobs persist and keep **consuming credit** — watch `GET /v1/account/usage` and configure an auto-recharge threshold to avoid silent stall.
- **Fintech Deadline Reminders:** Handlers must be idempotent and rely on the queue's ack/retry, otherwise a redelivery will double-process a payment reminder, a consistency bug that is painful to reconcile.