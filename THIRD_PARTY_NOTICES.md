# Third-party notices

Hatırlatıcı is distributed under GPL-3.0-or-later. The Flatpak also uses the components below under their own licenses. This inventory describes version 2.0.0 packaging; the authoritative license texts shipped by each upstream project remain controlling.

| Component | Packaged version | Role | License |
| --- | ---: | --- | --- |
| Python | Freedesktop 26.08 runtime version | Runtime | Python-2.0 |
| Qt Base, Qt Wayland client, and Qt SVG | 6.11.1 | Source-built GUI and SVG runtime | Primarily LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only, depending on file/module, plus bundled third-party terms; see the installed upstream `LICENSES`/REUSE metadata |
| PyQt6 | 6.11.0 | Python Qt bindings | GPL-3.0-only for the free/GPL build |
| PyQt6-sip | 13.12.0 | PyQt runtime support | BSD-2-Clause |
| sip | 6.16.1 | Build-only bindings generator | BSD-2-Clause |
| PyQt-builder | 1.19.1 | Build-only PyQt backend | BSD-2-Clause |
| packaging | 26.3 | Build-only marker/version parser required by SIP | Apache-2.0 OR BSD-2-Clause |
| PLY | 3.11 | Build-only parser used by sip | BSD-3-Clause |
| pycairo | 1.29.1 | Cairo Python bindings | LGPL-2.1-only OR MPL-1.1 |
| PyGObject | 3.56.3 | Portal/GObject bindings | LGPL-2.1-or-later |
| pycparser | 3.0 | C parser used by cffi | BSD-3-Clause |
| cffi | 2.1.1 | Python foreign-function interface | MIT-0 |
| cryptography | 50.0.0 | AES-GCM and HKDF primitives | Apache-2.0 OR BSD-3-Clause |
| maturin | 1.14.1 | Build-only Rust/Python backend | MIT OR Apache-2.0 |

The production manifest installs upstream license files for Qt Base/Wayland/SVG, PyQt6, PyQt6-sip, sip, PyQt-builder, packaging, PLY, pycairo, PyGObject, pycparser, cffi, and cryptography below the application's Flatpak license directory. The cffi 2.1.1 sdist identifies its terms as “MIT No Attribution” (SPDX `MIT-0`). Python and platform-provided system-library notices are supplied by the Freedesktop runtime ref. The 32 pinned Cargo packages in cryptography's locked source graph, including build and target-specific dependencies, are inventoried from their exact vendored `Cargo.toml` and checksum metadata; every bundled root license/notice text is installed beside the deterministic `CARGO_DEPENDENCIES.json` report. Maturin and its separate Cargo graph are build-only, and the maturin executable and sources are removed from the exported application.

Upstream sources:

- Python: https://www.python.org/
- Qt: https://www.qt.io/
- PyQt: https://www.riverbankcomputing.com/software/pyqt/
- PyQt6-sip: https://pypi.org/project/PyQt6-sip/
- sip: https://www.riverbankcomputing.com/software/sip/
- PyQt-builder: https://pypi.org/project/PyQt-builder/
- packaging: https://pypi.org/project/packaging/26.3/
- PLY: https://github.com/dabeaz/ply
- pycairo: https://pycairo.readthedocs.io/
- PyGObject: https://pygobject.gnome.org/
- pycparser: https://github.com/eliben/pycparser
- cffi: https://cffi.readthedocs.io/
- cryptography: https://cryptography.io/
- maturin: https://www.maturin.rs/

No compatibility conflict was identified between these selected terms and GPL-3.0-or-later distribution of Hatırlatıcı. This notice is an engineering inventory, not legal advice.
