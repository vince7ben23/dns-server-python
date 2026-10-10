import unittest

from app.header import DNSHeader


class TestDNSHeaderToBytes(unittest.TestCase):
    def test_header_is_12_bytes(self):
        self.assertEqual(len(DNSHeader().to_bytes()), 12)

    def test_default_header_is_all_zero(self):
        self.assertEqual(DNSHeader().to_bytes(), b"\x00" * 12)

    def test_packet_identifier_is_big_endian(self):
        self.assertEqual(DNSHeader(packet_identifier=1234).to_bytes()[:2], b"\x04\xd2")

    def test_query_response_indicator_is_highest_bit_of_flags(self):
        self.assertEqual(
            DNSHeader(query_response_indicator=1).to_bytes()[2:4], b"\x80\x00"
        )

    def test_operation_code_occupies_bits_after_query_response_indicator(self):
        self.assertEqual(DNSHeader(operation_code=0b1111).to_bytes()[2:4], b"\x78\x00")

    def test_authoritative_answer_truncation_recursion_desired_bits(self):
        self.assertEqual(DNSHeader(authoritative_answer=1).to_bytes()[2:4], b"\x04\x00")
        self.assertEqual(DNSHeader(truncation=1).to_bytes()[2:4], b"\x02\x00")
        self.assertEqual(DNSHeader(recursion_desired=1).to_bytes()[2:4], b"\x01\x00")

    def test_recursion_available_reserved_response_code_bits(self):
        self.assertEqual(DNSHeader(recursion_available=1).to_bytes()[2:4], b"\x00\x80")
        self.assertEqual(DNSHeader(reserved=0b111).to_bytes()[2:4], b"\x00\x70")
        self.assertEqual(DNSHeader(response_code=0b1111).to_bytes()[2:4], b"\x00\x0f")

    def test_counts_are_big_endian(self):
        header = DNSHeader(
            question_count=1,
            answer_record_count=2,
            authority_record_count=3,
            additional_record_count=0x0102,
        )
        self.assertEqual(
            header.to_bytes()[4:],
            b"\x00\x01\x00\x02\x00\x03\x01\x02",
        )

    def test_stage_expected_response_header(self):
        header = DNSHeader(packet_identifier=1234, query_response_indicator=1)
        self.assertEqual(
            header.to_bytes(),
            b"\x04\xd2\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00",
        )


class TestDNSHeaderValidation(unittest.TestCase):
    def test_rejects_field_overflow(self):
        with self.assertRaises(ValueError):
            DNSHeader(query_response_indicator=2)
        with self.assertRaises(ValueError):
            DNSHeader(operation_code=16)
        with self.assertRaises(ValueError):
            DNSHeader(packet_identifier=0x10000)


if __name__ == "__main__":
    unittest.main()
