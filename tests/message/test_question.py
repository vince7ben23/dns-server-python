import unittest

from app.message.question import DNSQuestion
from tests.fixtures import UINT16_OVERFLOW


class TestDNSQuestionToBytes(unittest.TestCase):
    def test_stage_expected_question(self):
        self.assertEqual(
            DNSQuestion(name="codecrafters.io").to_bytes(),
            b"\x0ccodecrafters\x02io\x00"  # name
            + bytes([0, 1])  # type: A
            + bytes([0, 1]),  # class: IN
        )

    def test_type_and_class_are_big_endian(self):
        question = DNSQuestion(name="a", record_type=5, record_class=0x0102)
        self.assertEqual(question.to_bytes()[-4:], bytes([0, 5]) + b"\x01\x02")


class TestDNSQuestionValidation(unittest.TestCase):
    def test_rejects_field_overflow(self):
        cases = [
            {"record_type": UINT16_OVERFLOW},
            {"record_class": -1},
        ]
        for kwargs in cases:
            with self.subTest(**kwargs), self.assertRaises(ValueError):
                DNSQuestion(name="a", **kwargs)


if __name__ == "__main__":
    unittest.main()
