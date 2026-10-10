## Payment Alerts & Holds

Northwind Books watches incoming and outgoing payments for duplicates and unusual activity.

### Duplicate-payment alerts

When a payment looks like it might duplicate an earlier one, an alert appears under **Payments → Alerts**. Each alert has a **match confidence**:
- **Exact**: same client, same amount, same reference number within 7 days.
- **Probable**: same client and amount, different reference.
- **Possible**: same amount only, or similar client names.

#### Dismissing a false positive

Possible and probable matches are often legitimate, such as two separate orders for the same amount.
1. Open the alert and compare the two payments (client, reference, date).
2. If they are separate payments, click **Dismiss → Not a duplicate** and enter a reason. A reason is required and is kept for audit.
3. Dismissed alerts stay in the **Payment Alerts Audit** report.

### Payment holds

Large or unusual incoming payments (for example, over **$25,000** from a client’s first-ever payment) may be **held for review**. Customers can’t release held funds themselves. Northwind’s Risk team reviews every hold within **1 business day**. If you need the funds urgently (for example, for payroll), open a support ticket and mark it urgent. Support can’t release holds or guarantee timing.

### Notification settings

Each user controls their own alert emails: **Profile → Notifications**. Choose instant, daily digest, or off for each alert type.
