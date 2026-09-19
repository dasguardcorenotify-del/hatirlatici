#!/usr/bin/env python3
"""Shared, accessible language selector for every application surface."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QToolButton, QWidget

import l10n


class LanguageMenuButton(QToolButton):
    """Native-name language menu with one Qt-provided menu indicator."""

    languageChanged = pyqtSignal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        language: str = "en",
    ) -> None:
        super().__init__(parent)
        self.setObjectName("languageSelector")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(44)

        self._language = "en"
        menu = QMenu(self)
        menu.setObjectName("languageMenu")
        self.setMenu(menu)

        for code in l10n.SUPPORTED_LANGUAGES:
            action = QAction(l10n.LANGUAGE_NAMES[code], menu)
            action.setData(code)
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked=False, selected=code: self.select_language(
                    selected
                )
            )
            menu.addAction(action)

        self.select_language(language, emit=False)

    def current_language(self) -> str:
        return self._language

    def select_language(self, language: str, *, emit: bool = True) -> None:
        normalized = l10n.normalize_language(language)
        changed = normalized != self._language
        self._language = normalized
        self.setText(l10n.LANGUAGE_NAMES[normalized])
        for action in self.menu().actions():
            action.setChecked(action.data() == normalized)
        if emit and changed:
            self.languageChanged.emit(normalized)
