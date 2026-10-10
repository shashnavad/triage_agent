## API & Webhooks

### Environments

| **Environment** | **Base URL** | **Notes** |
| --- | --- | --- |
| Production | https://api.northwindbooks.example/v1 | Live data |
| Sandbox | https://sandbox-api.northwindbooks.example/v1 | Test data only; free on all plans |

API keys are **environment-specific**. A sandbox key returns 401 Unauthorized against production, and vice versa. Generate keys under **Settings → Developers → API Keys** (Owner/Admin only).

### Authentication

Send your key in the header:

Authorization: Bearer <api_key>

Keys expire **365 days** after creation. An expired key returns 401 with "error": "key_expired".

### Rate limits

- **600 requests per minute** per account (production), 120/min (sandbox).

- Going over the limit returns 429 Too Many Requests with a Retry-After header (in seconds).

- Bulk endpoints (e.g., POST /v1/invoices/resend, max 100 IDs) count as one request.

### Common errors

| **Code** | **Meaning** |
| --- | --- |
| 400 | Malformed request; see error.details |
| 401 | Missing, invalid, expired, or wrong-environment key |
| 403 | Key is valid but lacks permission for this resource |
| 404 | Resource not found or not in your account |
| 429 | Rate limited |
| 5xx | Northwind-side error; retry with backoff and contact support if it continues |

### Webhooks

Set up endpoints under **Settings → Developers → Webhooks**. Events include invoice.paid, invoice.overdue, payment.held, import.completed.

- Deliveries are signed with HMAC-SHA256 (X-Northwind-Signature header).

- Your endpoint must return a 2xx within **10 seconds**.

- Failed deliveries are retried **5 times** with exponential backoff over about 2 hours.

- If an endpoint fails continuously for **24 hours**, it’s automatically **disabled**. Re-enable it from **Settings → Developers → Webhooks**. Events from the disabled period can be replayed from the **Delivery Log** for up to 7 days.

If your endpoint is healthy, returns 2xx, and shows as enabled, but deliveries still aren’t arriving, contact support. It may be an issue on our side.
