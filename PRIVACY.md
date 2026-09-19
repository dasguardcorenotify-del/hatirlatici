# Privacy

Last updated: 2026-08-21

Hatırlatıcı is local-first. It does not include analytics, telemetry, advertising SDKs, behavioral tracking, a Hatırlatıcı cloud account, or cloud synchronization.

## Data stored locally

Reminder records, delivery history, settings, backups, locks, and logs are stored in the XDG configuration, data, and state directories supplied to the application. In the Flatpak build these locations are sandbox-scoped beneath the application's private directory.

SMTP credentials are encrypted before they are written to the local credential vault. The encryption key is derived from secret material returned by the desktop Secret portal. File permissions and encryption reduce accidental disclosure, but cannot protect data from a party that already controls the user's active desktop account or can modify the application process.

Hatırlatıcı does not intentionally collect or transmit reminder content to the project maintainers.

## Network use

The Flatpak has network permission because optional email delivery connects to the SMTP server configured by the user. A reminder's email fields and message content are sent to that SMTP service when email delivery is enabled. The SMTP provider's privacy terms then apply.

Opening a documentation, source, issue, privacy, or future support link hands the URL to the system's default browser. Browser and destination-site policies apply after that handoff.

No other network service is required for PC-only reminders. The application does not process payments.

## Deleting data

Delete reminders and history from the application where available. To remove all sandboxed data after uninstalling, use Flatpak's data-removal option only after making any backup you want to keep:

```bash
flatpak uninstall --delete-data io.github.dasguardcorenotify_del.hatirlatici
```

This operation is destructive and cannot be undone without a separate backup.

## Questions

Use the support channel described in [SUPPORT.md](SUPPORT.md). Never attach passwords, App Passwords, credential-vault files, access tokens, or reminder data to a public issue.
