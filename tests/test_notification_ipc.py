import io
import json
import unittest


import notification_ipc


class NotificationIPCTests(
    unittest.TestCase
):
    def test_unicode_round_trip(self):
        payload = (
            notification_ipc
            .encode_payload(
                "İlaç zamanı",
                "Saat 20.00'de al.",
                token="worker-a1",
            )
        )

        self.assertLessEqual(
            len(payload),
            notification_ipc
            .MAX_PAYLOAD_BYTES,
        )

        self.assertEqual(
            notification_ipc
            .read_payload(
                io.BytesIO(
                    payload
                )
            ),
            (
                "İlaç zamanı",
                "Saat 20.00'de al.",
                "worker-a1",
            ),
        )

    def test_text_is_bounded_before_pipe_write(
        self,
    ):
        payload = (
            notification_ipc
            .encode_payload(
                "S" * 1000,
                "G" * 10000,
                token="worker-b2",
            )
        )

        subject, body, token = (
            notification_ipc
            .decode_payload(
                payload
            )
        )

        self.assertEqual(
            len(subject),
            notification_ipc
            .MAX_TITLE_CHARS,
        )

        self.assertEqual(
            len(body),
            notification_ipc
            .MAX_BODY_CHARS,
        )

        self.assertEqual(
            token,
            "worker-b2",
        )

    def test_oversized_input_is_rejected(self):
        with self.assertRaises(
            notification_ipc
            .NotificationPayloadError
        ):
            notification_ipc.decode_payload(
                b"x"
                * (
                    notification_ipc
                    .MAX_PAYLOAD_BYTES
                    + 1
                )
            )

    def test_schema_is_fail_closed(self):
        payload = json.dumps(
            {
                "version": 1,
                "subject": "Title",
                "body": "Body",
                "token": "worker-c3",
                "unexpected": "not accepted",
            }
        ).encode("utf-8")

        with self.assertRaises(
            notification_ipc
            .NotificationPayloadError
        ):
            notification_ipc.decode_payload(
                payload
            )


if __name__ == "__main__":
    unittest.main()
