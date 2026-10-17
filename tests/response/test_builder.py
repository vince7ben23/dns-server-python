import unittest

from app.message.answer import DNSAnswer
from app.message.header import HEADER_SIZE, DNSHeader
from app.message.parser import parse_header
from app.message.question import DNSQuestion
from app.response.builder import (
    OPCODE_STANDARD_QUERY,
    RCODE_NO_ERROR,
    RCODE_NOT_IMPLEMENTED,
    build_response,
)

_QUESTIONS = [DNSQuestion(name="codecrafters.io")]


def response_header(
    request_header: DNSHeader, questions: list[DNSQuestion] = _QUESTIONS
) -> DNSHeader:
    return parse_header(build_response(request_header, questions))


def answer_for(name: str) -> DNSAnswer:
    rdata = bytes([8, 8, 8, 8])  # 8.8.8.8
    return DNSAnswer(name=name, rdata_length=len(rdata), rdata=rdata)


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
        header = response_header(DNSHeader(operation_code=OPCODE_STANDARD_QUERY))
        self.assertEqual(header.response_code, RCODE_NO_ERROR)

    def test_non_standard_query_is_not_implemented(self):
        for opcode in (1, 2, 15):
            with self.subTest(opcode=opcode):
                header = response_header(DNSHeader(operation_code=opcode))
                self.assertEqual(header.response_code, RCODE_NOT_IMPLEMENTED)

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

    def test_counts_match_number_of_questions(self):
        for count in (0, 1, 2):
            questions = [DNSQuestion(name=f"q{i}.com") for i in range(count)]
            with self.subTest(count=count):
                header = response_header(DNSHeader(), questions)

                self.assertEqual(header.question_count, count)
                self.assertEqual(header.answer_record_count, count)
                self.assertEqual(header.authority_record_count, 0)
                self.assertEqual(header.additional_record_count, 0)


class TestBuildResponseBody(unittest.TestCase):
    def test_question_and_answer_mimic_request_name(self):
        question = DNSQuestion(name="example.com")
        expected = question.to_bytes() + answer_for("example.com").to_bytes()
        self.assertEqual(
            build_response(DNSHeader(), [question])[HEADER_SIZE:], expected
        )

    def test_all_questions_come_before_their_answers(self):
        # 順序為 Q1 Q2 A1 A2, name 皆不壓縮
        first = DNSQuestion(name="codecrafters.io")
        second = DNSQuestion(name="mail.codecrafters.io")
        expected = (
            first.to_bytes()
            + second.to_bytes()
            + answer_for(first.name).to_bytes()
            + answer_for(second.name).to_bytes()
        )
        self.assertEqual(
            build_response(DNSHeader(), [first, second])[HEADER_SIZE:], expected
        )


if __name__ == "__main__":
    unittest.main()
