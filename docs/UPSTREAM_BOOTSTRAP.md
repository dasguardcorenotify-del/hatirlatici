# Upstream bootstrap record

This Git repository was created from verified source snapshots because no original `.git` directory could be recovered.

The reconstructed commits were created on the actual bootstrap date. Their commit timestamps were not altered to imitate the snapshot dates.

## Reconstruction commits

1. `939590b6c1355b493a1c578c3602f16da97eb7ec` — history: reconstruct verified source state 1 (Git tree `1e7047d0dd4059fc635e9726d45abb261f9ed498`).
2. `245090873035463d269cbadda39436072e8af17e` — history: reconstruct verified source state 2 (Git tree `c47938d243dfbe342d37006fea5c82df8bbfc9ec`).
3. `53a07d1aec2fa4839b4b5d1c74da52c55ded087b` — history: reconstruct verified source state 3 (Git tree `cd77d2a2e05d6b273b5daa9d85a884ae8de180ce`).
4. `35d31f7002c969cd2b04677531b472b2cecfb341` — import: add current verified 2.0.0 source (Git tree `24c448618efafe4412b25455131ffe77b0d0bb97`).

The fourth reconstruction commit matches the verified canonical source tree before provenance/disclosure documentation was added.

## F3-R3 continuation

This packaging continuation migrates the candidate to Freedesktop 26.08, strengthens desktop AppStream metadata, and requires a clean, reproducible x86_64 source build before any public remote is added. The build evidence is kept outside the immutable release source tree.

## F3-R3 source-build dependency closure

Freedesktop 26.08 supplies Python 3.14. SIP 6.16.1 imports `packaging.markers` during the PyQt source build, so the official packaging 26.3 source distribution is pinned as a build-only module. Its license texts remain installed while the Python package itself is removed from the exported runtime.
