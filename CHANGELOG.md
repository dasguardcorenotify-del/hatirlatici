# Changelog

All notable public-release changes are documented here.

## [2.0.0] - 2026-08-21

### Added

- Local-first Linux reminder workflow with PC, email, and combined delivery modes
- Guided first-run setup in English, Turkish, German, Spanish, and Russian
- Gmail App Password guidance and custom SMTP configuration
- Portal-backed encrypted local credential vault
- Desktop notification actions, history, backups, single-instance handling, and system-tray operation
- Flatpak packaging, localized desktop metadata, AppStream metadata, public documentation, and CI scaffolding

### Security

- XDG- and Flatpak-scoped runtime paths with no broad home or host filesystem permission
- TLS certificate verification and TLS 1.2 minimum for SMTP
- Pinned offline source builds for bundled dependencies; architecture-specific Python wheels removed

### Release notes

- No analytics, advertising, tracking, cloud account, or cloud sync is included.
- Six synthetic-data store screenshots are included and pinned to the `v2.0.0` tag. No donation destination is published because no real owner-verified URL is available.
- Flathub submission is externally blocked by the current generative-AI policy unless an applicable exception is granted or the policy changes.
