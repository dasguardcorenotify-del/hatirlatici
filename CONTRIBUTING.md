# Contributing

Thank you for helping improve Hatırlatıcı. Contributions should be small enough to review, include tests for behavior changes, and avoid real user data.

## Before opening a change

1. Open an issue for substantial behavior or packaging changes.
2. Work from a clean branch based on the current public default branch.
3. Keep all user-facing text in the localization catalog and update all five supported locales.
4. Use synthetic addresses under reserved domains and synthetic reminders in tests.
5. Never commit credentials, tokens, vault files, private paths, runtime CSV files, screenshots containing personal data, or generated Flatpak build directories.

## Local checks

Run the Python suite with an offscreen Qt backend:

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m compileall -q .
```

Validate desktop metadata:

```bash
desktop-file-validate packaging/flatpak/io.github.dasguardcorenotify_del.hatirlatici.desktop
appstreamcli validate --no-net --explain packaging/flatpak/io.github.dasguardcorenotify_del.hatirlatici.metainfo.xml
```

Build local checkouts only with the `.Devel.yml` manifest described in [README.md](README.md). The canonical production manifest must continue to use a published immutable source archive with the exact SHA-256 digest.

## Packaging rules

- Do not add binary wheels, architecture-only dependency artifacts, network access during build, unpinned branches, or broad sandbox permissions.
- Regenerate `cargo-sources-*.json` with the official Flatpak cargo generator whenever the associated Rust lockfile changes.
- Preserve dependency license files and update [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) with every dependency change.
- A release version and date must agree across source, AppStream, changelog, source archive, tag, and artifacts.

## License

By contributing, you agree that your contribution is provided under GPL-3.0-or-later, unless a separately identified file states another compatible license. Do not submit material you do not have the right to license.
