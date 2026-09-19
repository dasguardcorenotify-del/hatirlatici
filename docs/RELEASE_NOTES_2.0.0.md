# Hatırlatıcı 2.0.0

Hatırlatıcı is a local-first Linux reminder application with desktop, optional email, and combined delivery. Version 2.0.0 provides English, Turkish, German, Spanish, and Russian interfaces.

## Highlights

- Guided five-language first-run setup for PC-only, Gmail, custom SMTP, or combined delivery
- Portal-based desktop notifications with Complete and Snooze actions
- Optional native Python SMTP with certificate verification and TLS 1.2 or newer
- Secret Portal-backed AES-256-GCM credential storage
- Local reminder history, recurrence, catch-up, leasing, system-tray, and single-instance behavior
- Freedesktop 25.08 Flatpak with Qt 6.11.1, PyQt6 6.11.0, and Python dependencies built from pinned source archives
- No analytics, advertising, tracking, cloud account, broad home access, host service, `notify-send`, or `msmtp` dependency

## Install the direct bundle

Download these four release assets into one directory:

- `hatirlatici-2.0.0.flatpak`
- `hatirlatici-2.0.0.tar.xz`
- `io.github.dasguardcorenotify_del.hatirlatici.yml`
- `SHA256SUMS`

Verify and install:

```bash
sha256sum -c SHA256SUMS
flatpak install --user ./hatirlatici-2.0.0.flatpak
flatpak run io.github.dasguardcorenotify_del.hatirlatici
```

The direct bundle is unsigned and does not provide automatic updates. Future versions must be downloaded and verified explicitly unless a signed update repository is published later.

## Delivery truth and privacy

Local leasing prevents normal duplicate dispatch, but no SMTP client can guarantee mathematically exact once-only network delivery if a process stops after the server accepts a message and before local finalization. Email remains optional; PC-only reminders need no mail account.

Application data remains inside the Flatpak-scoped XDG directories. Credentials are encrypted locally and are never intentionally printed. See `PRIVACY.md`, `SECURITY.md`, and `THIRD_PARTY_NOTICES.md` in the tagged source.

No donation destination is included because no real owner-verified public URL is available. This release contains disclosed AI-assisted code and documentation. Flathub acceptance remains subject to reviewer discretion, and the human owner will handle submission and review communications manually.
