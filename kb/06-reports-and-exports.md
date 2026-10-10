## Reports & Exports

### Standard reports

Find these under **Reports → Library**:
- **Profit & Loss**: income and expenses for a period
- **AR Aging**: unpaid invoices grouped by how overdue they are (current, 1–30, 31–60, 61–90, 90+ days)
- **Sales Tax Summary**: tax collected per invoice, used for tax filings
- **Upcoming Recurring Invoices**: recurring invoices scheduled to go out, by date
- **Payment Alerts Audit**: all duplicate-payment alerts and their dismissals

### Downloading a report

- Open the report and set filters.

- Click **Export** and choose **CSV** or **PDF**.

- Large exports (over 10,000 rows) are prepared in the background. You’ll get an email with a download link when it’s ready.

Download links are valid for **7 days**. If a link has expired, go to **Reports → History**, find the export, and click **Regenerate link**. You don’t need to run the report again.

### Scheduling a report

- Open the report and set the filters you want.

- Click **Schedule**.

- Choose how often (daily, weekly on a chosen weekday, or monthly), the format, and recipients. Recipients must be team members on your account.

- Click **Save**. Scheduled reports are sent at 6:00 AM in your business’s time zone.

Manage or cancel schedules from **Reports → Scheduled**.

### Dates and time zones in exports

- **Timestamp** fields (e.g., paid_at, sent_at) are exported in **UTC**.

- **Date-only** fields (e.g., invoice_date, due_date) are exported exactly as stored and are **not** time-zone adjusted. They should always match what the app shows.

### Row limits

- In-app tables show up to 500 rows per page.

- CSV exports have no row limit. PDF exports are limited to 2,000 rows.
