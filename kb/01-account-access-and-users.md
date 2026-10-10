## Account Access & User Management

### Resetting your password

- Go to the Northwind Books login page and click **Forgot password**.

- Enter the email address on your account. A reset link is sent within 5 minutes.

- Reset links expire after **60 minutes**. If yours expired, request a new one.

If you don’t receive the email, check your spam/junk folder and make sure no-reply@northwindbooks.example isn’t blocked.

### Two-factor authentication (2FA)

- 2FA is required for all users. Codes are sent by SMS or an authenticator app.

- If a user loses access to their 2FA device, **any Owner or Admin** on the account can reset it: **Settings → Team → [user] → Reset 2FA**.

- If the **only** Owner/Admin on an account is locked out, Northwind Support must verify their identity before resetting 2FA. This can’t be self-served. Open a ticket and our team will contact you.

### Adding team members and assigning roles

Owners and Admins can add people from **Settings → Team → Invite member**.

| **Role** | **Can do** |
| --- | --- |
| Owner / Admin | Everything, including team management, billing, bank connections, and SSO |
| Bookkeeper | Create and edit invoices, record payments, reconcile bank transactions |
| Read-only | View invoices, transactions, and reports; can’t edit or export |

To give someone (for example, your external accountant) view-only access, invite them and pick **Read-only**. You can change roles at any time from the same screen.

### Single sign-on (SSO)

- SAML 2.0 SSO (Okta, Microsoft Entra ID, Google Workspace, OneLogin) is available on the **Scale plan** only.

- SSO is **set up by Northwind Support**, not self-served. To request it, an Owner submits their identity provider’s metadata XML through the Help Center form **“SSO Setup Request.”**

- Setup is completed within **5 business days** of receiving complete metadata. If you’re not on the Scale plan, contact your Account Manager.
