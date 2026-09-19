import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP_ID = "io.github.dasguardcorenotify_del.hatirlatici"
SCREENSHOT_BASE = (
    "https://raw.githubusercontent.com/dasguardcorenotify-del/hatirlatici/"
    "v2.0.0/docs/screenshots"
)
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
SCREENSHOTS = (
    (
        "01-today-new-reminder.png",
        (1000, 700),
        {
            "en": "Create a reminder from the Today view",
            "tr": "Bugün görünümünde yeni hatırlatıcı oluşturma",
            "de": "Eine Erinnerung in der Heute-Ansicht erstellen",
            "es": "Crear un recordatorio desde la vista Hoy",
            "ru": "Создание напоминания в представлении «Сегодня»",
        },
    ),
    (
        "02-reminder-list.png",
        (1000, 700),
        {
            "en": "Review scheduled reminders in the list",
            "tr": "Planlanmış hatırlatıcıları listede gözden geçirme",
            "de": "Geplante Erinnerungen in der Liste prüfen",
            "es": "Revisar los recordatorios programados en la lista",
            "ru": "Просмотр запланированных напоминаний в списке",
        },
    ),
    (
        "03-history.png",
        (1000, 700),
        {
            "en": "Review reminder delivery history",
            "tr": "Hatırlatıcı teslim geçmişini gözden geçirme",
            "de": "Den Zustellverlauf der Erinnerungen prüfen",
            "es": "Revisar el historial de entrega de recordatorios",
            "ru": "Просмотр истории доставки напоминаний",
        },
    ),
    (
        "04-settings-local-security.png",
        (1000, 700),
        {
            "en": "Configure language, delivery, and local security settings",
            "tr": "Dil, teslimat ve yerel güvenlik ayarlarını yapılandırma",
            "de": "Sprache, Zustellung und lokale Sicherheit konfigurieren",
            "es": "Configurar el idioma, la entrega y la seguridad local",
            "ru": "Настройка языка, доставки и локальной безопасности",
        },
    ),
    (
        "05-first-run-gmail-guide.png",
        (980, 730),
        {
            "en": "Follow the first-run Gmail App Password guide",
            "tr": "İlk çalıştırmada Gmail Uygulama Şifresi rehberini izleme",
            "de": "Der Anleitung für Gmail-App-Passwörter beim ersten Start folgen",
            "es": "Seguir la guía inicial de contraseñas de aplicación de Gmail",
            "ru": "Руководство по паролю приложения Gmail при первом запуске",
        },
    ),
    (
        "06-support-and-language.png",
        (1000, 700),
        {
            "en": "Access About, privacy, issue-reporting, and support options",
            "tr": "Hakkında, gizlilik, sorun bildirme ve destek seçeneklerine erişme",
            "de": "Info, Datenschutz, Fehlerberichte und Support aufrufen",
            "es": "Acceder a Acerca de, privacidad, informes de errores y ayuda",
            "ru": "Доступ к сведениям, конфиденциальности, сообщениям об ошибках и поддержке",
        },
    ),
)


class PackagingReleaseTests(unittest.TestCase):
    def test_appstream_identity_and_release(self):
        path = ROOT / "packaging" / "flatpak" / f"{APP_ID}.metainfo.xml"
        component = ET.parse(path).getroot()
        self.assertEqual(component.attrib.get("type"), "desktop-application")
        self.assertEqual(component.findtext("id"), APP_ID)
        self.assertEqual(component.findtext("metadata_license"), "CC0-1.0")
        self.assertEqual(component.findtext("project_license"), "GPL-3.0-or-later")
        release = component.find("./releases/release")
        self.assertIsNotNone(release)
        self.assertEqual(release.attrib, {"version": "2.0.0", "date": "2026-08-21"})
        self.assertEqual(
            release.findtext("url[@type='details']"),
            "https://github.com/dasguardcorenotify-del/hatirlatici/releases/tag/v2.0.0",
        )
        branding = component.find("branding")
        self.assertIsNotNone(branding)
        colors = {
            (node.attrib.get("type"), node.attrib.get("scheme_preference")): (node.text or "").strip()
            for node in branding.findall("color")
        }
        self.assertEqual(
            colors,
            {("primary", "light"): "#0E7C86", ("primary", "dark"): "#20C7C9"},
        )
        requirements = component.find("requires")
        self.assertIsNotNone(requirements)
        self.assertEqual(
            {node.text for node in requirements.findall("control")},
            {"keyboard", "pointing"},
        )
        display = requirements.find("display_length")
        self.assertIsNotNone(display)
        self.assertEqual(display.attrib, {"compare": "ge"})
        self.assertEqual((display.text or "").strip(), "768")

    def test_approved_store_screenshots_and_no_donation(self):
        path = ROOT / "packaging" / "flatpak" / f"{APP_ID}.metainfo.xml"
        component = ET.parse(path).getroot()
        screenshots = component.findall("./screenshots/screenshot")
        self.assertEqual(len(screenshots), len(SCREENSHOTS))
        expected_files = {item[0] for item in SCREENSHOTS}
        actual_files = {path.name for path in (ROOT / "docs" / "screenshots").glob("*.png")}
        self.assertEqual(actual_files, expected_files)
        for index, (node, (filename, dimensions, expected_captions)) in enumerate(
            zip(screenshots, SCREENSHOTS, strict=True)
        ):
            self.assertEqual(node.attrib, {"type": "default"} if index == 0 else {})
            images = node.findall("image")
            self.assertEqual(len(images), 1)
            self.assertEqual(
                images[0].attrib,
                {"type": "source", "width": str(dimensions[0]), "height": str(dimensions[1])},
            )
            self.assertEqual((images[0].text or "").strip(), f"{SCREENSHOT_BASE}/{filename}")
            captions = {
                caption.attrib.get(XML_LANG, "en"): (caption.text or "").strip()
                for caption in node.findall("caption")
            }
            self.assertEqual(captions, expected_captions)
        self.assertFalse([url for url in component.findall("url") if url.attrib.get("type") == "donation"])

    def test_source_build_policy(self):
        production = (ROOT / f"{APP_ID}.yml").read_text(encoding="utf-8")
        development = (ROOT / f"{APP_ID}.Devel.yml").read_text(encoding="utf-8")
        self.assertNotIn(".whl", production)
        self.assertNotIn("only-arches", production)
        self.assertNotIn("base:", production)
        self.assertNotIn("base-version:", production)
        self.assertNotIn("--no-talk-name", production)
        self.assertNotIn("--nofilesystem", production)
        self.assertNotIn("--nosocket", production)
        self.assertNotIn("type: dir", production)
        self.assertIn("type: dir", development)
        self.assertIn("hatirlatici-2.0.0.tar.xz", production)
        for manifest in (production, development):
            self.assertIn("runtime: org.freedesktop.Platform", manifest)
            self.assertIn("runtime-version: '26.08'", manifest)
            self.assertIn("sdk: org.freedesktop.Sdk", manifest)
            self.assertIn("qtbase-everywhere-src-6.11.1.tar.xz", manifest)
            self.assertIn("qtwayland-everywhere-src-6.11.1.tar.xz", manifest)
            self.assertIn("qtsvg-everywhere-src-6.11.1.tar.xz", manifest)
            self.assertLess(
                manifest.index("qtsvg-everywhere-src-6.11.1.tar.xz"),
                manifest.index("qtwayland-everywhere-src-6.11.1.tar.xz"),
            )
            self.assertEqual(manifest.count("-DFEATURE_wayland_client=ON"), 1)
            self.assertEqual(manifest.count("-DFEATURE_wayland_server=OFF"), 2)
            self.assertIn("-DFEATURE_glibc_fortify_source=OFF", manifest)
            self.assertEqual(manifest.count("-DFEATURE_vulkan=OFF"), 1)
            self.assertEqual(manifest.count("--disabled-feature=PyQt_Vulkan"), 1)
            self.assertNotIn("-DQT_FEATURE_", manifest)
            self.assertIn("qtbase-client-only-contract", manifest)
            self.assertIn("QT_FEATURE_wayland_server=-1", manifest)
            self.assertIn("QT_FEATURE_glibc_fortify_source=-1", manifest)
            self.assertIn("FLATPAK_SDK_FORTIFY_SOURCE=3", manifest)
            self.assertNotIn("/lib/libQt6OpenGL*.so*", manifest)
            self.assertIn("- /lib/libQt6OpenGLWidgets.so*", manifest)
            for cleanup_entry in (
                "- /lib64/pkgconfig",
                "- /lib/python*/site-packages/cairo/include",
                "- /bin/cffi-gen-src",
                "- /bin/pylupdate6",
                "- /bin/pyuic6",
                "- /bin/sip-install",
                "- /plugins/wayland-graphics-integration-client/libdmabuf-server.so",
                "- /plugins/wayland-graphics-integration-client/libdrm-egl-server.so",
                "- /plugins/wayland-graphics-integration-client/libshm-emulation-server.so",
            ):
                self.assertIn(cleanup_entry, manifest)
            self.assertIn("QMAKE_CFLAGS_RELEASE += ${CFLAGS}", manifest)
            self.assertIn("QMAKE_CXXFLAGS_RELEASE += ${CXXFLAGS}", manifest)
            self.assertIn("QMAKE_LFLAGS += ${LDFLAGS}", manifest)
            self.assertIn("CONFIG += no_qt_rpath", manifest)
            self.assertIn("pyqt6-6.11.0.tar.gz", manifest)
            self.assertIn("packaging-26.3.tar.gz", manifest)
            self.assertIn("94edc256424af38762eb31306eed28beb9f0efc50a8837492c9d6fd6004aed79", manifest)
            self.assertIn("- /lib/python*/site-packages/packaging*", manifest)
            self.assertEqual(manifest.count("name: python-packaging-build-tool"), 1)
            self.assertLess(
                manifest.index("name: python-packaging-build-tool"),
                manifest.index("  - name: sip\n"),
            )
            self.assertNotIn("qtdeclarative", manifest.lower())
            self.assertNotIn("qtwebengine", manifest.lower())
            self.assertNotIn("qtmultimedia", manifest.lower())
        for name in ("cargo-sources-maturin.json", "cargo-sources-cryptography.json"):
            sources = json.loads((ROOT / "packaging" / "flatpak" / name).read_text(encoding="utf-8"))
            self.assertTrue(sources)
            for source in sources:
                if source.get("type") == "archive":
                    self.assertRegex(source.get("sha256", ""), r"^[0-9a-f]{64}$")

    def test_desktop_identity(self):
        desktop = (ROOT / "packaging" / "flatpak" / f"{APP_ID}.desktop").read_text(encoding="utf-8")
        self.assertRegex(desktop, re.compile(r"^Exec=hatirlatici$", re.MULTILINE))
        self.assertRegex(desktop, re.compile(rf"^Icon={re.escape(APP_ID)}$", re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
