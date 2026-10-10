import unittest

from app.message.question import DNSQuestion


class TestDNSQuestionToBytes(unittest.TestCase):
    def test_stage_expected_question(self):
        self.assertEqual(
            DNSQuestion(name="codecrafters.io").to_bytes(),
            b"\x0ccodecrafters\x02io\x00\x00\x01\x00\x01",
        )

    def test_type_and_class_are_big_endian(self):
        question = DNSQuestion(name="a", record_type=5, record_class=0x0102)
        self.assertEqual(question.to_bytes()[-4:], b"\x00\x05\x01\x02")


class TestDNSQuestionValidation(unittest.TestCase):
    def test_rejects_field_overflow(self):
        with self.assertRaises(ValueError):
            DNSQuestion(name="a", record_type=0x10000)
        with self.assertRaises(ValueError):
            DNSQuestion(name="a", record_class=-1)


if __name__ == "__main__":
    unittest.main()
