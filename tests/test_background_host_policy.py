import os
import unittest
from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

GENERATED_DIRS = {
    ".flatpak-builder",
    ".git",
    "__pycache__",
    "dist",
    "repo",
}


def _public_files():
    for directory, names, filenames in os.walk(ROOT):
        names[:] = [
            name
            for name in names
            if name not in GENERATED_DIRS
            and not name.startswith("build-")
        ]
        base = Path(directory)
        for filename in filenames:
            yield base / filename


class BackgroundHostPolicyTests(
    unittest.TestCase
):
    def test_legacy_host_service_stack_absent(
        self,
    ):
        token = (
            "sys"
            + "temd"
        )

        hits = []

        for path in _public_files():

            try:
                text = (
                    path.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                )
            except OSError:
                continue

            if token in text.lower():
                hits.append(
                    str(
                        path.relative_to(
                            ROOT
                        )
                    )
                )

        self.assertEqual(
            hits,
            [],
            hits,
        )

    def test_background_components_exist(
        self,
    ):
        self.assertTrue(
            (
                ROOT
                / "background_portal.py"
            ).is_file()
        )

        self.assertTrue(
            (
                ROOT
                / "delivery_scheduler.py"
            ).is_file()
        )


if __name__ == "__main__":
    unittest.main()
