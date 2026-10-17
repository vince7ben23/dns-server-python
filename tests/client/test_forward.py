import unittest
from unittest import mock

from app.client import forward
from app.client.forward import (
    ForwardingLookup,
    UpstreamError,
    build_query,
    parse_reply,
)
from app.message.answer import DNSAnswer
from app.message.header import DNSHeader
from app.message.parser import parse_header, parse_questions
from app.message.question import DNSQuestion

_RESOLVER_ADDR = ("127.0.0.1", 5353)
_QUESTION = DNSQuestion(name="codecrafters.io")
_PACKET_ID = 1234
_TIMEOUT_SECONDS = 3.0


def a_record(name: str, last_octet: int) -> DNSAnswer:
    rdata = bytes([10, 0, 0, last_octet])
    return DNSAnswer(name=name, rdata_length=len(rdata), rdata=rdata)


def reply_bytes(answers: list[DNSAnswer], query_response_indicator: int = 1) -> bytes:
    """組出 resolver 對 _QUESTION 的 reply."""
    header = DNSHeader(
        query_response_indicator=query_response_indicator,
        question_count=1,
        answer_record_count=len(answers),
    )
    return (
        header.to_bytes()
        + _QUESTION.to_bytes()
        + b"".join(answer.to_bytes() for answer in answers)
    )


class TestBuildQuery(unittest.TestCase):
    def test_single_question_query(self):
        query = build_query(_PACKET_ID, _QUESTION, recursion_desired=1)
        header = parse_header(query)

        self.assertEqual(header.packet_identifier, _PACKET_ID)
        self.assertEqual(header.query_response_indicator, 0)
        self.assertEqual(header.recursion_desired, 1)
        self.assertEqual(parse_questions(query, header.question_count)[0], [_QUESTION])


class TestParseReply(unittest.TestCase):
    def test_returns_answers_after_question(self):
        answers = [a_record(_QUESTION.name, 1), a_record(_QUESTION.name, 2)]
        self.assertEqual(parse_reply(reply_bytes(answers)), answers)

    def test_rejects_query_instead_of_response(self):
        with self.assertRaisesRegex(ValueError, "not a response"):
            parse_reply(reply_bytes([], query_response_indicator=0))

    def test_rejects_truncated_answer(self):
        with self.assertRaises(ValueError):
            parse_reply(reply_bytes([a_record(_QUESTION.name, 1)])[:-1])


def lookup_with(recv_result):
    """用假 socket 執行一次 ForwardingLookup, recvfrom 回傳 (或 raise) recv_result.

    回傳 (lookup 的結果或 raise 的 exception, 假 socket).
    """
    fake_socket = mock.MagicMock()
    fake_socket.__enter__.return_value = fake_socket
    fake_socket.recvfrom.side_effect = [recv_result]
    lookup = ForwardingLookup(_RESOLVER_ADDR, timeout=_TIMEOUT_SECONDS)
    with mock.patch.object(forward.socket, "socket", return_value=fake_socket):
        try:
            result = lookup(_QUESTION)
        except UpstreamError as e:
            result = e
    return result, fake_socket


class TestForwardingLookup(unittest.TestCase):
    def test_sends_single_question_query_to_resolver(self):
        _, fake_socket = lookup_with((reply_bytes([]), _RESOLVER_ADDR))

        fake_socket.settimeout.assert_called_once_with(_TIMEOUT_SECONDS)
        query, address = fake_socket.sendto.call_args.args
        self.assertEqual(address, _RESOLVER_ADDR)
        self.assertEqual(parse_header(query).question_count, 1)
        self.assertEqual(parse_questions(query, 1)[0], [_QUESTION])

    def test_returns_answers_from_reply(self):
        answers = [a_record(_QUESTION.name, 1)]
        result, fake_socket = lookup_with((reply_bytes(answers), _RESOLVER_ADDR))

        self.assertEqual(result, answers)
        fake_socket.__exit__.assert_called_once()

    def test_wraps_failures_as_upstream_error(self):
        failures = {
            "timeout": TimeoutError("timed out"),
            "socket_error": OSError("unreachable"),
            "malformed_reply": (bytes(1), _RESOLVER_ADDR),
        }
        for case, recv_result in failures.items():
            with self.subTest(case=case):
                result, _ = lookup_with(recv_result)
                self.assertIsInstance(result, UpstreamError)


if __name__ == "__main__":
    unittest.main()
