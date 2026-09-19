# Support

## Start here

Check [README.md](README.md) for installation and email configuration and [PRIVACY.md](PRIVACY.md) for data locations. Confirm that the issue occurs with the latest public 2.0.x release and an unmodified profile before reporting it.

When the public repository is available, use its issue tracker:

https://github.com/dasguardcorenotify-del/hatirlatici/issues

For security vulnerabilities, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## A useful bug report

Include:

- Hatırlatıcı version and installation source
- Linux distribution, desktop environment, and Flatpak version
- Whether the session is Wayland or X11
- Clear reproduction steps, expected result, and actual result
- Relevant sanitized application output

Never include an email password, Gmail App Password, SMTP credential, token, vault file, private reminder, personal email address, or an entire unsanitized settings/data directory.

## Email delivery checks

- Confirm the reminder has email delivery enabled.
- For Gmail, use an App Password rather than the normal account password.
- Confirm the system clock and certificate store are correct.
- Verify the selected STARTTLS or implicit-TLS mode and port with the SMTP provider.
- Check the provider's account activity and rate limits.

Delivery is best-effort and can be delayed, rejected, or duplicated by failures outside the application. Do not use Hatırlatıcı as the sole mechanism for safety-critical, medical, legal, or emergency notifications.

## Donations

No donation destination is currently configured or verified. There is no in-app payment processing and no feature is reserved for donors.
