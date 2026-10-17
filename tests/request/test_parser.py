import unittest

from app.message.header import DNSHeader
from app.request.parser import HEADER_SIZE, parse_header


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


if __name__ == "__main__":
    unittest.main()
