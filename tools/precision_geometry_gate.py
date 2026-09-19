#!/usr/bin/env python3
"""Deterministic first-run geometry gate for host and Flatpak execution."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", choices=("1.0", "1.25", "1.5"), default="1.0")
    parser.add_argument("--inject-failure", action="store_true")
    return parser.parse_args()


ARGS = _arguments()
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_SCALE_FACTOR"] = ARGS.scale
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

TEMP_PROFILE = tempfile.TemporaryDirectory(prefix="hatirlatici-geometry-")
PROFILE_ROOT = Path(TEMP_PROFILE.name)
ISOLATED_DIRS = {
    "XDG_CONFIG_HOME": PROFILE_ROOT / "config",
    "XDG_DATA_HOME": PROFILE_ROOT / "data",
    "XDG_STATE_HOME": PROFILE_ROOT / "state",
    "XDG_CACHE_HOME": PROFILE_ROOT / "cache",
    "XDG_RUNTIME_DIR": PROFILE_ROOT / "runtime",
    "HOME": PROFILE_ROOT / "home",
    "TMPDIR": PROFILE_ROOT / "tmp",
}
for environment_name, directory in ISOLATED_DIRS.items():
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    os.environ[environment_name] = str(directory)
tempfile.tempdir = str(ISOLATED_DIRS["TMPDIR"])

CODE_ROOT_OVERRIDE = os.environ.get(
    "HATIRLATICI_GEOMETRY_CODE_ROOT",
    "",
).strip()
if CODE_ROOT_OVERRIDE:
    ROOT = Path(CODE_ROOT_OVERRIDE).resolve()
    CODE_ROOT_SOURCE = "INSTALLED_OVERRIDE"
else:
    ROOT = Path(__file__).resolve().parent.parent
    CODE_ROOT_SOURCE = "CHECKOUT"
if not (
    (ROOT / "l10n.py").is_file()
    and (ROOT / "ui_v2" / "first_run_setup.py").is_file()
):
    print("PRECISION_GEOMETRY_GATE=FAIL_INVALID_CODE_ROOT")
    TEMP_PROFILE.cleanup()
    raise SystemExit(41)
for candidate in (ROOT, ROOT / "ui_v2"):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QLabel,
    QLineEdit,
    QScrollArea,
    QWidget,
)

import l10n
from first_run_setup import ChoiceCard, GuidedFirstRunDialog


LANGUAGES = l10n.SUPPORTED_LANGUAGES
SCENARIOS = (
    ("pc", None, (0, 1, 4)),
    ("email", "gmail", (0, 1, 2, 3, 4)),
    ("email", "custom", (0, 1, 2, 4)),
    ("both", "gmail", (0, 1, 2, 3, 4)),
    ("both", "custom", (0, 1, 2, 4)),
)
SIZES = (
    (960, 680),
    (1000, 700),
    (1120, 760),
    (1280, 800),
    (1366, 768),
    (1536, 960),
)


def _name(widget: QWidget) -> str:
    return widget.objectName() or widget.__class__.__name__


def _inside_scroll(widget: QWidget, dialog: QWidget) -> bool:
    parent = widget.parentWidget()
    while parent is not None and parent is not dialog:
        if isinstance(parent, QScrollArea):
            return True
        parent = parent.parentWidget()
    return False


def main() -> int:
    app = QApplication.instance() or QApplication([])
    dialog = GuidedFirstRunDialog(preview=True)
    dialog.show()
    app.processEvents()

    failures: list[tuple[str, str, str, str]] = []
    warnings: list[tuple[str, str, str, str]] = []
    checks = 0

    def fail(kind: str, context: str, widget: QWidget, detail: str) -> None:
        failures.append((kind, context, _name(widget), detail))

    def check_label(widget: QLabel, context: str) -> None:
        text = widget.text()
        if not text:
            return
        rect = widget.contentsRect()
        if rect.width() <= 0 or rect.height() <= 0:
            fail("ZERO_TEXT_GEOMETRY", context, widget, f"{rect.width()}x{rect.height()}")
            return
        metrics = QFontMetrics(widget.font())
        if widget.wordWrap():
            # Measure text inside the content rectangle. QLabel.heightForWidth
            # includes stylesheet padding, while contentsRect excludes it;
            # comparing those two produces false clipping reports.
            required = metrics.boundingRect(
                0,
                0,
                rect.width(),
                10000,
                int(Qt.TextFlag.TextWordWrap),
                text,
            ).height()
            if required > rect.height() + 2:
                fail(
                    "LABEL_VERTICAL_CLIP",
                    context,
                    widget,
                    f"required={required} actual={rect.height()} text={text!r}",
                )
        else:
            required_width = metrics.horizontalAdvance(text)
            required_height = metrics.height()
            if required_width > rect.width() + 2:
                fail(
                    "LABEL_HORIZONTAL_CLIP",
                    context,
                    widget,
                    f"required={required_width} actual={rect.width()} text={text!r}",
                )
            if required_height > rect.height() + 2:
                fail(
                    "LABEL_VERTICAL_CLIP",
                    context,
                    widget,
                    f"required={required_height} actual={rect.height()} text={text!r}",
                )

    def check_button(widget: QAbstractButton, context: str) -> None:
        text = widget.text()
        if not text:
            return
        rect = widget.contentsRect()
        metrics = QFontMetrics(widget.font())
        reserved = 28 if widget.menu() is not None else 24
        if widget.isCheckable() or widget.__class__.__name__ == "QCheckBox":
            reserved += 24
        usable = max(1, rect.width() - reserved)
        required = max(metrics.horizontalAdvance(line) for line in (text.splitlines() or [""]))
        if required > usable + 2:
            fail(
                "BUTTON_HORIZONTAL_CLIP",
                context,
                widget,
                f"required={required} usable={usable} text={text!r}",
            )
        required_height = len(text.splitlines() or [""]) * metrics.lineSpacing()
        if required_height > rect.height() + 2:
            fail(
                "BUTTON_VERTICAL_CLIP",
                context,
                widget,
                f"required={required_height} actual={rect.height()} text={text!r}",
            )

    def check_bounds(widget: QWidget, context: str) -> None:
        if _inside_scroll(widget, dialog):
            return
        rect = widget.rect()
        top_left = widget.mapTo(dialog, rect.topLeft())
        bottom_right = widget.mapTo(dialog, rect.bottomRight())
        if (
            top_left.x() < -2
            or top_left.y() < -2
            or bottom_right.x() > dialog.width() + 2
            or bottom_right.y() > dialog.height() + 2
        ):
            fail(
                "WINDOW_OVERFLOW",
                context,
                widget,
                f"widget=({top_left.x()},{top_left.y()})-({bottom_right.x()},{bottom_right.y()}) "
                f"window={dialog.width()}x{dialog.height()}",
            )

    def audit(context: str) -> None:
        nonlocal checks
        active = dialog.pages.currentWidget()
        relevant_roots = (dialog.sidebar, dialog.findChild(QWidget, "setupFooter"), active)
        for widget in dialog.findChildren(QWidget):
            if not any(widget is root or root.isAncestorOf(widget) for root in relevant_roots if root):
                continue
            if widget.isHidden():
                continue
            checks += 1
            check_bounds(widget, context)
            if isinstance(widget, QLabel):
                check_label(widget, context)
            elif isinstance(widget, QAbstractButton):
                check_button(widget, context)

        scrolls = []
        if isinstance(active, QScrollArea):
            scrolls.append(active)
        if active is not None:
            scrolls.extend(active.findChildren(QScrollArea))
        for scroll in scrolls:
            if scroll.horizontalScrollBar().maximum() != 0:
                fail(
                    "HORIZONTAL_SCROLL",
                    context,
                    scroll,
                    f"maximum={scroll.horizontalScrollBar().maximum()}",
                )

    if dialog.minimumWidth() != 960 or dialog.minimumHeight() != 680:
        fail(
            "MINIMUM_SIZE_CONTRACT",
            "startup",
            dialog,
            f"actual={dialog.minimumWidth()}x{dialog.minimumHeight()}",
        )
    if dialog.pages.count() != 5:
        fail("PAGE_COUNT", "startup", dialog.pages, f"actual={dialog.pages.count()}")
    if dialog.language_selector.menu() is None:
        fail("LANGUAGE_MENU_MISSING", "startup", dialog.language_selector, "menu=None")
    if any(glyph in dialog.language_selector.text() for glyph in ("▾", "▼")):
        fail("DOUBLE_LANGUAGE_ARROW", "startup", dialog.language_selector, dialog.language_selector.text())
    if len(dialog.language_selector.menu().actions()) != 5:
        fail(
            "LANGUAGE_COUNT",
            "startup",
            dialog.language_selector,
            f"actual={len(dialog.language_selector.menu().actions())}",
        )
    else:
        menu = dialog.language_selector.menu()
        menu_width = menu.sizeHint().width()
        menu_metrics = QFontMetrics(menu.font())
        required_menu_width = max(
            menu_metrics.horizontalAdvance(action.text())
            for action in menu.actions()
        ) + 40
        if required_menu_width > menu_width + 2:
            fail(
                "LANGUAGE_MENU_CLIP",
                "startup",
                menu,
                f"required={required_menu_width} actual={menu_width}",
            )
    if not dialog.language_selector.accessibleName():
        fail("ACCESSIBLE_NAME", "startup", dialog.language_selector, "missing")
    for card in dialog.findChildren(ChoiceCard):
        if not card.accessibleName():
            fail("ACCESSIBLE_NAME", "startup", card, "missing")

    for language in LANGUAGES:
        dialog.language_selector.select_language(language)
        app.processEvents()
        for channel, provider, pages in SCENARIOS:
            dialog._set_channel(channel)
            if provider is not None:
                dialog._set_provider(provider)
            for page in pages:
                dialog.pages.setCurrentIndex(page)
                dialog._update_navigation()
                app.processEvents()
                for width, height in SIZES:
                    dialog.resize(width, height)
                    app.processEvents()
                    context = (
                        f"lang={language};path={channel}/{provider or '-'};"
                        f"page={page + 1};size={width}x{height};scale={ARGS.scale}"
                    )
                    if dialog.width() != width or dialog.height() != height:
                        fail(
                            "REQUESTED_SIZE_NOT_HONORED",
                            context,
                            dialog,
                            f"actual={dialog.width()}x{dialog.height()}",
                        )
                    audit(context)

    if ARGS.inject_failure:
        failures.append(("SYNTHETIC_FAILURE", "selftest", "gate", "intentional"))

    counts = Counter(item[0] for item in failures)
    warning_counts = Counter(item[0] for item in warnings)
    print(f"SCALE_FACTOR={ARGS.scale}")
    print(f"LANGUAGES_TESTED={len(LANGUAGES)}")
    print(f"REAL_USER_PATHS_TESTED={len(SCENARIOS)}")
    print(f"WINDOW_SIZES_TESTED={len(SIZES)}")
    print(f"TOTAL_WIDGET_CHECKS={checks}")
    print(f"TRUE_FAILURES={len(failures)}")
    print(f"WARNINGS={len(warnings)}")
    for kind, count in sorted(counts.items()):
        print(f"FAIL_COUNT_{kind}={count}")
    for kind, count in sorted(warning_counts.items()):
        print(f"WARN_COUNT_{kind}={count}")

    seen: set[tuple[str, str, str]] = set()
    for kind, context, widget, detail in failures:
        signature = (kind, widget, detail)
        if signature in seen:
            continue
        seen.add(signature)
        print(f"TRUE_FAIL={kind} | {context} | {widget} | {detail}")
        if len(seen) >= 40:
            break

    gate = "FAIL" if failures else "PASS"
    print(f"GEOMETRY_CODE_ROOT_SOURCE={CODE_ROOT_SOURCE}")
    print(f"PRECISION_GEOMETRY_GATE={gate}")
    dialog.close()
    TEMP_PROFILE.cleanup()
    return 41 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
