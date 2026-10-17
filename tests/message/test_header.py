import unittest

from app.message.header import DNSHeader

# 16-bit 欄位可容納的最小溢位值
_UINT16_OVERFLOW = 1 << 16


class TestDNSHeaderToBytes(unittest.TestCase):
    def test_header_is_12_bytes(self):
        self.assertEqual(len(DNSHeader().to_bytes()), 12)

    def test_default_header_is_all_zero(self):
        self.assertEqual(DNSHeader().to_bytes(), bytes(12))

    def test_packet_identifier_is_big_endian(self):
        # 1234 = 4 * 256 + 210
        self.assertEqual(
            DNSHeader(packet_identifier=1234).to_bytes()[:2], bytes([4, 210])
        )

    def test_query_response_indicator_is_highest_bit_of_flags(self):
        self.assertEqual(
            DNSHeader(query_response_indicator=1).to_bytes()[2:4],
            bytes([0b10000000, 0]),
        )

    def test_operation_code_occupies_bits_after_query_response_indicator(self):
        self.assertEqual(
            DNSHeader(operation_code=15).to_bytes()[2:4], bytes([0b01111000, 0])
        )

    def test_authoritative_answer_truncation_recursion_desired_bits(self):
        self.assertEqual(
            DNSHeader(authoritative_answer=1).to_bytes()[2:4], bytes([0b100, 0])
        )
        self.assertEqual(DNSHeader(truncation=1).to_bytes()[2:4], bytes([0b10, 0]))
        self.assertEqual(
            DNSHeader(recursion_desired=1).to_bytes()[2:4], bytes([0b1, 0])
        )

    def test_recursion_available_reserved_response_code_bits(self):
        self.assertEqual(
            DNSHeader(recursion_available=1).to_bytes()[2:4], bytes([0, 0b10000000])
        )
        self.assertEqual(DNSHeader(reserved=7).to_bytes()[2:4], bytes([0, 0b01110000]))
        self.assertEqual(
            DNSHeader(response_code=15).to_bytes()[2:4], bytes([0, 0b00001111])
        )

    def test_counts_are_big_endian(self):
        header = DNSHeader(
            question_count=1,
            answer_record_count=2,
            authority_record_count=3,
            additional_record_count=0x0102,
        )
        self.assertEqual(
            header.to_bytes()[4:],
            bytes([0, 1, 0, 2, 0, 3]) + b"\x01\x02",
        )

    def test_stage_expected_response_header(self):
        header = DNSHeader(packet_identifier=1234, query_response_indicator=1)
        self.assertEqual(
            header.to_bytes(),
            bytes([4, 210])  # ID: 1234
            + bytes([0b10000000, 0])  # flags: 只有 QR = 1
            + bytes(8),  # 4 個 count 皆為 0
        )


class TestDNSHeaderValidation(unittest.TestCase):
    def test_rejects_field_overflow(self):
        with self.assertRaises(ValueError):
            DNSHeader(query_response_indicator=2)
        with self.assertRaises(ValueError):
            DNSHeader(operation_code=16)
        with self.assertRaises(ValueError):
            DNSHeader(packet_identifier=_UINT16_OVERFLOW)


if __name__ == "__main__":
    unittest.main()
