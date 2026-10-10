## Invoicing

### Sending an invoice

Create an invoice from **Invoices → New invoice**, then click **Send**. Your client gets an email with a link to view and pay the invoice online.

- Payment links in invoice emails expire after **14 days**. The invoice itself stays open, so expiry only affects the link.

- To resend a single invoice, open it and click **Resend**. This creates a new payment link and invalidates the old one.

#### Client says they never received the invoice

- Check that the client’s email address on the invoice is correct.

- Ask the client to check spam/junk and quarantine folders. Invoices come from invoices@northwindbooks.example.

- If the invoice was sent more than 14 days ago, the link has expired. Use **Resend**.

#### Resending many invoices at once

There is no bulk-resend option in the web app. To resend many invoices, use the API endpoint POST /v1/invoices/resend, which accepts up to **100 invoice IDs per request** (see *API & Webhooks*). If you don’t use the API, ask your Account Manager for a one-time bulk resend.

### Invoice statuses

| **Status** | **Meaning** |
| --- | --- |
| Draft | Not sent yet |
| Sent | Emailed to the client, not yet viewed |
| Viewed | The client opened the invoice |
| Partially Paid | Some payment recorded |
| Paid | Fully paid |
| Overdue | Past the due date and not fully paid |
| Void | Cancelled |

### Recurring invoices

- Set up from **Invoices → Recurring → New schedule**. Choose weekly, monthly, quarterly, or yearly.

- The **next send date** appears on each schedule under **Recurring → [schedule] → Next invoice**.

- For a list across all schedules, run the **Upcoming Recurring Invoices** report (see *Reports & Exports*).

### Currencies

Northwind Books supports **40 currencies**. Set a default currency in **Settings → Business**, and override it per client. Exchange rates update daily.

### Payment details

Clients pay through the secure payment page. **Never** ask clients to email card numbers. Northwind Support can’t take card details over email or chat, and can’t charge a card manually. If a client’s payment failed, they should retry from the payment link or use a different payment method.
