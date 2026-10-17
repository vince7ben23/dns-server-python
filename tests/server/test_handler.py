import unittest
from unittest import mock

from app.message.answer import DNSAnswer
from app.message.header import HEADER_SIZE, DNSHeader
from app.message.parser import parse_header
from app.message.question import DNSQuestion
from app.server.handler import fixed_lookup, handle_query
from app.server.response import build_response
from tests.fixtures import COMPRESSION_POINTER_BYTE, a_record

# 非 standard query 的 opcode (2 = server status request)
_OPCODE_STATUS = 2


class TestFixedLookup(unittest.TestCase):
    def test_answers_question_name_with_fixed_address(self):
        rdata = bytes([8, 8, 8, 8])  # 8.8.8.8
        self.assertEqual(
            fixed_lookup(DNSQuestion(name="codecrafters.io")),
            [DNSAnswer(name="codecrafters.io", rdata_length=len(rdata), rdata=rdata)],
        )


class TestHandleQuery(unittest.TestCase):
    def test_looks_up_each_question_and_merges_answers_in_order(self):
        header = DNSHeader(packet_identifier=1234, question_count=2)
        first = DNSQuestion(name="codecrafters.io")
        second = DNSQuestion(name="mail.codecrafters.io")
        answers = {
            first.name: [a_record(first.name, 1)],
            second.name: [a_record(second.name, 2)],
        }
        lookup = mock.Mock(side_effect=lambda question: answers[question.name])

        response = handle_query(
            header.to_bytes() + first.to_bytes() + second.to_bytes(), lookup
        )

        self.assertEqual([c.args[0] for c in lookup.call_args_list], [first, second])
        self.assertEqual(
            response,
            build_response(
                header, [first, second], answers[first.name] + answers[second.name]
            ),
        )

    def test_decodes_compressed_question_before_lookup(self):
        header = DNSHeader(question_count=2)
        first = DNSQuestion(name="codecrafters.io")
        # 第 2 個 question: "mail" 加上指向第 1 個 name (緊接在 header 之後) 的 pointer
        second_bytes = (
            b"\x04mail"
            + bytes([COMPRESSION_POINTER_BYTE, HEADER_SIZE])
            + bytes([0, 1, 0, 1])
        )
        lookup = mock.Mock(return_value=[])

        handle_query(header.to_bytes() + first.to_bytes() + second_bytes, lookup)

        self.assertEqual(
            lookup.call_args_list[1].args[0], DNSQuestion(name="mail.codecrafters.io")
        )

    def test_non_standard_query_skips_lookup(self):
        header = DNSHeader(operation_code=_OPCODE_STATUS, question_count=1)
        question = DNSQuestion(name="codecrafters.io")
        lookup = mock.Mock(return_value=[a_record(question.name, 1)])

        response = handle_query(header.to_bytes() + question.to_bytes(), lookup)

        lookup.assert_not_called()
        self.assertEqual(parse_header(response).answer_record_count, 0)

    def test_rejects_malformed_request(self):
        header = DNSHeader(question_count=1)
        request = header.to_bytes() + DNSQuestion(name="a").to_bytes()[:-1]
        lookup = mock.Mock()

        with self.assertRaises(ValueError):
            handle_query(request, lookup)
        lookup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
