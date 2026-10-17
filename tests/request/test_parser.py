import unittest

from app.message.header import DNSHeader
from app.message.question import DNSQuestion
from app.request.parser import (
    HEADER_SIZE,
    QUESTION_TYPE_CLASS_SIZE,
    parse_header,
    parse_question,
)


def header_bytes(flags_high: int = 0, flags_low: int = 0) -> bytes:
    """組出 12-byte header, ID 與各 count 皆為 0, 只指定 flags 的兩個 byte."""
    return bytes([0, 0, flags_high, flags_low]) + bytes(8)


class TestParseHeader(unittest.TestCase):
    def test_round_trip_with_all_fields_set(self):
        header = DNSHeader(
            packet_identifier=1234,
            query_response_indicator=1,
            operation_code=2,
            authoritative_answer=1,
            truncation=1,
            recursion_desired=1,
            recursion_available=1,
            reserved=5,
            response_code=3,
            question_count=1,
            answer_record_count=2,
            authority_record_count=3,
            additional_record_count=4,
        )
        self.assertEqual(parse_header(header.to_bytes()), header)

    def test_packet_identifier_and_counts_are_big_endian(self):
        data = bytes([4, 210]) + bytes(2) + bytes([0, 1, 0, 2, 0, 3, 1, 2])
        header = parse_header(data)

        self.assertEqual(header.packet_identifier, 1234)  # 4 * 256 + 210
        self.assertEqual(header.question_count, 1)
        self.assertEqual(header.answer_record_count, 2)
        self.assertEqual(header.authority_record_count, 3)
        self.assertEqual(header.additional_record_count, 258)  # 1 * 256 + 2

    def test_high_flags_byte(self):
        self.assertEqual(
            parse_header(header_bytes(0b10000000)).query_response_indicator, 1
        )
        self.assertEqual(parse_header(header_bytes(0b01111000)).operation_code, 15)
        self.assertEqual(parse_header(header_bytes(0b00000100)).authoritative_answer, 1)
        self.assertEqual(parse_header(header_bytes(0b00000010)).truncation, 1)
        self.assertEqual(parse_header(header_bytes(0b00000001)).recursion_desired, 1)

    def test_low_flags_byte(self):
        self.assertEqual(
            parse_header(header_bytes(0, 0b10000000)).recursion_available, 1
        )
        self.assertEqual(parse_header(header_bytes(0, 0b01110000)).reserved, 7)
        self.assertEqual(parse_header(header_bytes(0, 0b00001111)).response_code, 15)

    def test_ignores_data_after_header(self):
        question = b"\x0ccodecrafters\x02io\x00" + bytes([0, 1, 0, 1])
        self.assertEqual(parse_header(header_bytes() + question), DNSHeader())

    def test_rejects_data_shorter_than_header(self):
        with self.assertRaises(ValueError):
            parse_header(bytes(HEADER_SIZE - 1))


class TestParseQuestion(unittest.TestCase):
    def test_round_trip_after_header(self):
        question = DNSQuestion(name="codecrafters.io")
        data = header_bytes() + question.to_bytes()

        self.assertEqual(parse_question(data), (question, len(data)))

    def test_type_and_class_are_big_endian(self):
        data = header_bytes() + b"\x01a\x00" + bytes([0, 5, 1, 2])
        question, _ = parse_question(data)

        self.assertEqual(question.record_type, 5)
        self.assertEqual(question.record_class, 258)  # 1 * 256 + 2

    def test_starts_from_given_offset(self):
        question = DNSQuestion(name="a")
        offset = 5
        data = bytes(offset) + question.to_bytes()

        self.assertEqual(parse_question(data, offset), (question, len(data)))

    def test_rejects_missing_type_and_class(self):
        data = header_bytes() + b"\x01a\x00" + bytes(QUESTION_TYPE_CLASS_SIZE - 1)
        with self.assertRaisesRegex(ValueError, "type and class"):
            parse_question(data)

    def test_rejects_malformed_name(self):
        with self.assertRaises(ValueError):
            parse_question(header_bytes() + b"\x03ab")


if __name__ == "__main__":
    unittest.main()
