# Hatırlatıcı

Hatırlatıcı is a local-first reminder application for Linux. It schedules reminders on the device and can deliver them through desktop notifications, optional email, or both. It has no cloud account, analytics, advertising, or tracking.

Version 2.0.0 supports English, Turkish, German, Spanish, and Russian.

> Project status (2026-09-19): the source provenance has been verified and an honest upstream Git repository is being established. Runtime upgrade, clean multi-architecture build, public release assets, and Flathub review remain open. AI assistance is disclosed in [AI_ASSISTANCE_DISCLOSURE.md](AI_ASSISTANCE_DISCLOSURE.md), and source history reconstruction is documented in [docs/PROVENANCE.md](docs/PROVENANCE.md).

## Features

- Local reminder creation, history, and automatic local backups
- Desktop notifications with complete and snooze actions
- Optional Gmail or custom SMTP delivery
- Combined desktop-and-email delivery
- Encrypted local SMTP credential vault backed by the desktop Secret portal
- Single-instance desktop window and optional system-tray operation
- XDG-compliant, Flatpak-scoped configuration, data, and state
- Five interface languages: English, Turkish, German, Spanish, and Russian

Email transport is best-effort: no application can guarantee exactly-once delivery across arbitrary SMTP servers and network failures.

## Install

The intended release artifact is `hatirlatici-2.0.0.flatpak` on the project's GitHub release page. Do not use an unverified bundle. Once the public release exists, verify its checksum against the accompanying `SHA256SUMS`, then install it with:

```bash
flatpak install --user ./hatirlatici-2.0.0.flatpak
flatpak run io.github.dasguardcorenotify_del.hatirlatici
```

A direct bundle does not provide automatic updates unless a signed Flatpak repository is also configured.

## Configure email

Email is optional. PC-only reminders require no mail account.

For Gmail, enable two-step verification on the Google account, create an App Password in Google's account security settings, and enter that 16-character App Password during Hatırlatıcı setup. Do not enter the regular Google account password. Availability and wording of Google's App Password feature are controlled by Google and may vary by account policy.

For custom SMTP, provide the server hostname, port, account name, credential, and either STARTTLS or implicit TLS. Hatırlatıcı validates server certificates with the platform trust store and requires TLS 1.2 or newer. Test the settings before relying on email delivery.

Credentials are encrypted locally. They are not printed by normal operation, but local encryption is not a defense against an attacker who already controls the logged-in desktop session.

## Build from source

Install Flatpak, `flatpak-builder`, and the Flathub remote, then install the maintained build dependencies:

```bash
flatpak install --user flathub \
  org.freedesktop.Platform//25.08 \
  org.freedesktop.Sdk//25.08 \
  org.freedesktop.Sdk.Extension.rust-stable//25.08
```

For a checked-out source tree, use the explicitly development-only manifest:

```bash
flatpak-builder --user --install --force-clean \
  --install-deps-from=flathub \
  build-dir \
  io.github.dasguardcorenotify_del.hatirlatici.Devel.yml
```

The canonical production manifest is `io.github.dasguardcorenotify_del.hatirlatici.yml`. It consumes the immutable, hashed `hatirlatici-2.0.0.tar.xz` release asset and is expected to build without network access in the build sandbox. Qt 6.11.1, PyQt6, and the other Python dependencies are built from pinned, hashed source distributions on the Freedesktop 25.08 runtime; no architecture-specific Python wheels are used.

## Data, privacy, and security

Hatırlatıcı stores runtime files below the XDG directories supplied by the environment. In Flatpak these resolve inside the app's sandbox under `~/.var/app/io.github.dasguardcorenotify_del.hatirlatici`. The app has no broad home or host filesystem permission.

Read [PRIVACY.md](PRIVACY.md) for data handling and [SECURITY.md](SECURITY.md) for vulnerability reporting and the security model.

## Screenshots

Six approved version 2.0.0 screenshots captured with synthetic data are stored in [`docs/screenshots`](docs/screenshots). AppStream references their immutable `v2.0.0` raw paths; those URLs become reachable only after the repository and exact release tag are published. The release gate pins their filenames, dimensions, SHA-256 digests, URLs, and localized captions.

## Support and donations

See [SUPPORT.md](SUPPORT.md) for help and bug-reporting guidance. No donation URL is configured because no real public destination has been verified. Donations, if enabled later, will remain voluntary and will not unlock features.

## Contributing and license

Contributions are welcome under the process in [CONTRIBUTING.md](CONTRIBUTING.md). Hatırlatıcı is licensed under [GPL-3.0-or-later](LICENSE). Dependency notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
