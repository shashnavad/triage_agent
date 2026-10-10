## Data Imports (Clients & Products)

Use imports to add or update many clients or products at once.

### Supported formats and limits

- Supported file types: **CSV (UTF-8)** and **XLSX**. Other formats (XLS, TXT, PDF) are not supported.

- Maximum **5,000 rows** and **10 MB** per file. Split larger files.

- Download the current template from **Clients → Import → Download template** (or **Products → Import**). Always use the latest template. Older ones may be missing required columns.

### Required columns (client import)

client_name, email, currency, country

Optional columns include phone, tax_id, payment_terms_days, billing_address. The template doesn’t currently have a field for purchase order (PO) numbers.

### Processing time

- Imports up to 5,000 rows normally finish within **30 minutes**.

- You’ll get an email when processing finishes, with a count of created, updated, and failed rows.

- If an import has shown **Processing** for more than **2 hours**, it’s probably stuck. Don’t re-upload the same file, because that can create duplicates. Open a support ticket with the import ID.

### Common error codes

| **Code** | **Meaning** | **Fix** |
| --- | --- | --- |
| I-101 | Missing required column | Re-download the template and add the column |
| I-102 | File isn’t UTF-8 encoded | Re-save as “CSV UTF-8” |
| I-103 | File exceeds 5,000 rows or 10 MB | Split the file |
| I-104 | Invalid currency code | Use a 3-letter ISO code such as USD, EUR, GBP |
| I-105 | Duplicate email within file | Remove the duplicate row |
| I-106 | Unknown country | Use the country name or 2-letter code from the template’s *Lookup* tab |

Rows with errors are skipped. Valid rows in the same file are still imported.
