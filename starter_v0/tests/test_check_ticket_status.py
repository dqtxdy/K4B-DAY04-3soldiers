from __future__ import annotations

import unittest

from tools.check_ticket_status.tool import check_ticket_status


class CheckTicketStatusTests(unittest.TestCase):
    def test_returns_known_ticket_status(self) -> None:
        result = check_ticket_status("lab-1001")
        self.assertEqual(result["ticket_id"], "LAB-1001")
        self.assertEqual(result["status"], "in_progress")
        self.assertNotIn("summary", result)

    def test_returns_not_found_for_unknown_ticket(self) -> None:
        result = check_ticket_status("LAB-9999")
        self.assertEqual(result["error"], "not_found")

    def test_rejects_invalid_ticket_id(self) -> None:
        result = check_ticket_status("../../.env")
        self.assertEqual(result["error"], "invalid_ticket_id")


if __name__ == "__main__":
    unittest.main()
