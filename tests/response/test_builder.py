import unittest

from app.message.answer import DNSAnswer
from app.message.header import DNSHeader
from app.message.question import DNSQuestion
from app.request.parser import HEADER_SIZE, parse_header
from app.response.builder import build_response

_RCODE_NOT_IMPLEMENTED = 4
QUESTION = DNSQuestion(name="codecrafters.io")


def response_header(request_header: DNSHeader) -> DNSHeader:
    return parse_header(build_response(request_header, QUESTION))


class TestBuildResponseHeader(unittest.TestCase):
    def test_mimics_id_opcode_and_recursion_desired(self):
        request = DNSHeader(
            packet_identifier=4321, operation_code=2, recursion_desired=1
        )
        header = response_header(request)

        self.assertEqual(header.packet_identifier, 4321)
        self.assertEqual(header.operation_code, 2)
        self.assertEqual(header.recursion_desired, 1)

    def test_standard_query_has_no_error(self):
        self.assertEqual(response_header(DNSHeader(operation_code=0)).response_code, 0)

    def test_non_standard_query_is_not_implemented(self):
        for opcode in (1, 2, 15):
            with self.subTest(opcode=opcode):
                header = response_header(DNSHeader(operation_code=opcode))
                self.assertEqual(header.response_code, _RCODE_NOT_IMPLEMENTED)

    def test_fixed_flags_ignore_request(self):
        request = DNSHeader(
            authoritative_answer=1,
            truncation=1,
            recursion_available=1,
            reserved=7,
        )
        header = response_header(request)

        self.assertEqual(header.query_response_indicator, 1)
        self.assertEqual(header.authoritative_answer, 0)
        self.assertEqual(header.truncation, 0)
        self.assertEqual(header.recursion_available, 0)
        self.assertEqual(header.reserved, 0)

    def test_counts_match_one_question_and_one_answer(self):
        header = response_header(DNSHeader())

        self.assertEqual(header.question_count, 1)
        self.assertEqual(header.answer_record_count, 1)
        self.assertEqual(header.authority_record_count, 0)
        self.assertEqual(header.additional_record_count, 0)


class TestBuildResponseBody(unittest.TestCase):
    def test_question_and_answer_mimic_request_name(self):
        question = DNSQuestion(name="example.com")
        expected = (
            question.to_bytes()
            + DNSAnswer(
                name="example.com", rdata_length=4, rdata=bytes([8, 8, 8, 8])
            ).to_bytes()
        )
        self.assertEqual(build_response(DNSHeader(), question)[HEADER_SIZE:], expected)


if __name__ == "__main__":
    unittest.main()
