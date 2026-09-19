# Security policy

## Supported versions

Security fixes are planned for the latest 2.0.x public release. Pre-release source snapshots and locally modified builds are not supported release channels.

## Report a vulnerability

After the public GitHub repository is enabled, use its private **Report a vulnerability** form under the Security tab. Do not disclose an unpatched vulnerability in a public issue. If private vulnerability reporting is not available, do not post secrets or exploit details publicly; the repository owner must enable a private reporting channel before public release.

Include the affected version, Flatpak commit if known, environment, reproduction steps, impact, and the smallest safe diagnostic sample. Remove reminder text, email addresses, SMTP credentials, vault files, tokens, and unrelated logs.

No response-time or disclosure-date guarantee is made before a maintainer acknowledges the report. Please allow coordinated remediation before public disclosure.

## Security model

- Flatpak limits filesystem access to the application sandbox; the manifest does not grant broad home or host access.
- Network permission exists solely because users may configure SMTP delivery.
- SMTP uses certificate validation and TLS 1.2 or newer. Custom SMTP supports STARTTLS and implicit TLS.
- SMTP secrets are encrypted locally with AES-256-GCM using key material derived from the desktop Secret portal.
- Sensitive values are not intended to appear in command arguments, environment variables, routine logs, or exception messages.
- Desktop notifications and external links use desktop portals where supported.

These controls do not defend against a compromised operating system, a malicious SMTP provider, an attacker controlling the active user session, or a modified application build.

## Dependency updates

Flatpak dependencies are pinned by version and cryptographic hash. Updates must retain offline source builds, regenerate Rust vendor-source manifests from the matching lockfiles, preserve license notices, and pass the security and packaging test suites.
