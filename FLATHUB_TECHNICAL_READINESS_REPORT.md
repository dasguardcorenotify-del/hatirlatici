# Flathub technical readiness report

Assessment date: 2026-08-21  
Application: Hatırlatıcı 2.0.0  
Flatpak ID: `io.github.dasguardcorenotify_del.hatirlatici`

## Machine-readable state

```text
PUBLIC_RELEASE_READY=NO
FLATHUB_TECHNICAL_READY=NO
LOCAL_X86_64_FULL_SOURCE_BUILD=IN_PROGRESS
PRODUCTION_IMMUTABLE_SOURCE_CONTRACT=PENDING_FINAL_HASH
DESKTOP_FILE_VALIDATION=PASS
APPSTREAM_STRUCTURAL_VALIDATION=PASS
EFFECTIVE_PERMISSION_AUDIT=PENDING_FREEDESKTOP_BUILD
DONATION_EXTERNAL_OWNER_ACTION_REQUIRED=YES
SCREENSHOTS_ACCEPTED_AND_PINNED=YES
SCREENSHOT_URL_PUBLICATION_PENDING_TAG=YES
GITHUB_REPOSITORY_EXTERNAL_OWNER_ACTION_REQUIRED=YES
RELEASE_TAG_EXTERNAL_OWNER_ACTION_REQUIRED=YES
RELEASE_ASSET_EXTERNAL_OWNER_ACTION_REQUIRED=YES
AARCH64_BUILD_VERIFICATION_REQUIRED=YES
FLATHUB_GENERATIVE_AI_POLICY_GATE=BLOCKED
FLATHUB_PUBLISHED=NO
```

These values are deliberately conservative. They must not be converted to `YES` or `PASS` without the evidence described below.

## Runtime and source-build design

The manifest targets `org.freedesktop.Platform` and `org.freedesktop.Sdk` 25.08. Qt 6.11.1 and PyQt6 6.11.0 are built inside `/app` from official, pinned source archives. This design avoids the unrelated filesystem and session-bus permissions inherited by the KDE runtime and avoids the negative permission overrides rejected by Flathub's manifest linter.

The selected Qt build enables the desktop XCB and Wayland client platform plugins and the Qt Core, D-Bus, GUI, Network, OpenGL support, Widgets, and SVG runtime plugins needed by the application. Concurrent, SQL, XML, Test, PrintSupport, EGLFS, LinuxFB, VNC, Vulkan, Qt Declarative/Quick, Multimedia, and WebEngine are not included. PyQt exposes only `QtCore`, `QtDBus`, `QtGui`, `QtNetwork`, and `QtWidgets`.

Pinned primary sources:

- Qt Base 6.11.1: `d9594a31228aa23ad6b531719a29b45f0f3989fe6c136d45767ea179f233c1ac`
- Qt Wayland 6.11.1: `95788aa502f75441d4edf65932b235f76523084e13dbbb7b9ee2d207b32bd9b3`
- Qt SVG 6.11.1: `7f3cf02f4824bf03c2c5859ea6db173bf1482a1daf24e6cdf7bc78cfa26a8a94`
- PyQt6 6.11.0: `45dd60aa69976de1918b5ced6b4e7b6a25abd2a919ecef5fd5826ecc76718889`
- sip 6.16.1, PyQt-builder 1.19.1, PyQt6-sip 13.12.0, and PLY 3.11 are also pinned by SHA-256 in the manifests.

The local runtime refs checked on 2026-08-21 were:

| Ref | Version/tool | Commit |
| --- | --- | --- |
| `org.freedesktop.Platform/x86_64/25.08` | freedesktop-sdk 25.08.16 | `bd44a6230581917d04f89812a4c21090c304d390edb73995af1c2f9fd8abf4e8` |
| `org.freedesktop.Sdk/x86_64/25.08` | Python 3.13.15, CMake 4.4.2, Ninja 1.13.2, GCC 15.2.0 | `b90ed309cc1d505dea48b6a2121c5dcfac22868120eee643b0596d31f96b9bb8` |
| `org.freedesktop.Sdk.Extension.rust-stable/x86_64/25.08` | Rust build extension | `385427f6dabe6d297cced114496cfa6e38bb93fe4c6fbee7fdabb97dd141d29a` |

No Python wheel, `only-arches`, or `skip-arches` entry is used by the production manifest. The current local build is x86_64 only; Flathub's independent aarch64 build must pass before technical readiness can be claimed.

## Sandbox permission target

The complete application `finish-args` set is:

```text
--share=ipc
--socket=wayland
--socket=fallback-x11
--device=dri
--share=network
--talk-name=org.kde.StatusNotifierWatcher
```

Network access supports optional user-configured SMTP. `org.kde.StatusNotifierWatcher` is used for the optional system-tray icon. There is no host/home filesystem grant. The release gate rejects extra, negative, or inherited BaseApp permission declarations. Final evidence must come from the completed Freedesktop build's exported metadata.

## Immutable release-source contract

`io.github.dasguardcorenotify_del.hatirlatici.Devel.yml` is explicitly development-only and reads the checkout with `type: dir`. The canonical production manifest must fetch exactly:

```text
tag: v2.0.0
asset: hatirlatici-2.0.0.tar.xz
URL: https://github.com/dasguardcorenotify-del/hatirlatici/releases/download/v2.0.0/hatirlatici-2.0.0.tar.xz
```

`packaging/flatpak/create-release-source.sh` creates that versioned archive with a fixed file set, normalized ownership/mode/mtime, single-threaded XZ output, and no runtime data. The top-level production manifest is deliberately excluded so its final archive SHA-256 does not create a circular input. `release_gate.py --archive` checks the exact member set, every member's bytes against the checkout, deterministic metadata, archive digest, and the digest embedded in the production manifest. `--require-tag` additionally requires `v2.0.0` to identify `HEAD` and the canonical origin.

The final asset must be generated after all source and documentation changes, its real digest inserted into the production manifest, and the identical bytes attached to the exact `v2.0.0` release. No placeholder digest is permitted.

## Metadata and current validation

- `desktop-file-validate`: pass.
- `appstreamcli validate --no-net --explain`: structural pass.
- `appstreamcli --pedantic`: nine expected pre-publication reachability warnings: three for the repository, project homepage, and issue tracker, plus six for screenshot paths below the not-yet-published `v2.0.0` tag. These warnings are not waived and must disappear after the owner publishes the repository and exact tag.
- AppStream version/date contract: 2.0.0 / 2026-08-21.
- English, Turkish, German, Spanish, and Russian desktop/AppStream strings are present.
- No donation URL is published. Six synthetic-data screenshots passed visual/privacy review and are pinned by filename, dimensions, SHA-256 digest, immutable `v2.0.0` raw URL, and five-language caption in the release gate. Their URLs remain unreachable until the owner publishes the repository and exact tag; that publication dependency is not waived.

## License inventory requirement

The manifest explicitly installs first-party GPL-3.0-or-later and upstream license texts under `/app/share/licenses/io.github.dasguardcorenotify_del.hatirlatici`. Final build evidence must include the installed inventory for Qt Base/Wayland/SVG, PyQt6, PyQt6-sip, sip, PyQt-builder, PLY, pycairo, PyGObject, pycparser, cffi, cryptography, and the application. A deterministic build step reads the exact vendored metadata for all 32 Cargo packages in cryptography's locked source graph (including build and target-specific dependencies), installs every bundled root license/notice text, and emits `cryptography/cargo/CARGO_DEPENDENCIES.json`; the post-build gate matches that report back to the pinned Cargo source hashes and license-file digests. cffi 2.1.1's bundled license is MIT No Attribution (`MIT-0`), not ordinary MIT. The exact terms and upstream links are recorded in `THIRD_PARTY_NOTICES.md`.

## Publication and policy blockers

No repository, tag, GitHub release, Flatpak bundle, Flathub submission, or donation destination has been created by this work. The six accepted store screenshots exist locally, but publishing the repository and exact tag remains an external owner action.

More importantly, Flathub's current inclusion requirements explicitly prohibit applications containing AI-generated or AI-assisted code or documentation, and prohibit AI-generated submission pull requests and review communications. The policy says exceptions may be granted for mature, well-maintained projects. Hatırlatıcı discloses AI assistance and does not currently have the public history needed to claim that discretionary exception. Therefore an automated or AI-authored Flathub submission must not be opened, and `FLATHUB_GENERATIVE_AI_POLICY_GATE` remains `BLOCKED` unless Flathub itself grants a documented exception under the then-current policy.

Primary references checked on 2026-08-21:

- Flathub requirements: https://docs.flathub.org/docs/for-app-authors/requirements
- Qt Wayland requirements: https://doc.qt.io/qt-6/wayland-requirements.html
- Qt Linux/X11 requirements: https://doc.qt.io/qt-6/linux-requirements.html
- Qt configure options: https://doc.qt.io/qt-6/configure-options.html
- Qt official source archive index: https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/

This report is an engineering assessment, not a publication approval or legal opinion.
