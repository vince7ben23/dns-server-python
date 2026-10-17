import unittest
from unittest import mock

from app import main as main_module
from app.client.forward import UpstreamError
from app.message.header import HEADER_SIZE, DNSHeader
from app.message.question import DNSQuestion
from app.server.handler import fixed_lookup
from app.server.response import build_response
from tests.fixtures import COMPRESSION_POINTER_BYTE, a_record

_CLIENT_ADDR = ("127.0.0.1", 54321)
_REQUEST_HEADER = DNSHeader(packet_identifier=1234, question_count=1)
_REQUEST_QUESTION = DNSQuestion(name="codecrafters.io")
_REQUEST = _REQUEST_HEADER.to_bytes() + _REQUEST_QUESTION.to_bytes()
_EXPECTED_RESPONSE = build_response(
    _REQUEST_HEADER, [_REQUEST_QUESTION], fixed_lookup(_REQUEST_QUESTION)
)
_RESOLVER_ADDR = ("127.0.0.1", 5353)


def run_main_with(recv_results, argv=()):
    """用假 socket 執行 `main(argv)`, `recvfrom` 依序回傳 `recv_results` 的每一項.

    `main()` 是無窮迴圈, 最後一項應為 exception 讓它跳出.
    回傳 (socket class mock, 假 socket, logger mock).
    """
    fake_socket = mock.Mock()
    fake_socket.recvfrom.side_effect = recv_results
    with (
        mock.patch.object(
            main_module.socket, "socket", return_value=fake_socket
        ) as socket_cls,
        mock.patch.object(main_module, "logger") as logger,
    ):
        main_module.main(list(argv))
    return socket_cls, fake_socket, logger


class TestMain(unittest.TestCase):
    def test_binds_udp_socket_on_port_2053(self):
        socket_cls, fake_socket, _ = run_main_with([OSError("stop")])

        socket_cls.assert_called_once_with(
            main_module.socket.AF_INET, main_module.socket.SOCK_DGRAM
        )
        fake_socket.bind.assert_called_once_with(("127.0.0.1", 2053))

    def test_replies_with_response_built_from_request(self):
        request_header = DNSHeader(
            packet_identifier=4321, recursion_desired=1, question_count=1
        )
        question = DNSQuestion(name="example.com")
        _, fake_socket, _ = run_main_with(
            [
                (request_header.to_bytes() + question.to_bytes(), _CLIENT_ADDR),
                OSError("stop"),
            ]
        )

        expected = build_response(request_header, [question], fixed_lookup(question))
        fake_socket.sendto.assert_called_once_with(expected, _CLIENT_ADDR)

    def test_replies_to_compressed_questions_uncompressed(self):
        request_header = DNSHeader(packet_identifier=4321, question_count=2)
        first = DNSQuestion(name="codecrafters.io")
        # 第 2 個 question: "mail" 加上指向第 1 個 name (緊接在 header 之後) 的 pointer
        second_bytes = (
            b"\x04mail"
            + bytes([COMPRESSION_POINTER_BYTE, HEADER_SIZE])
            + bytes([0, 1, 0, 1])
        )
        request = request_header.to_bytes() + first.to_bytes() + second_bytes
        _, fake_socket, _ = run_main_with([(request, _CLIENT_ADDR), OSError("stop")])

        second = DNSQuestion(name="mail.codecrafters.io")
        expected = build_response(
            request_header,
            [first, second],
            fixed_lookup(first) + fixed_lookup(second),
        )
        fake_socket.sendto.assert_called_once_with(expected, _CLIENT_ADDR)

    def test_replies_to_each_request(self):
        other_addr = ("127.0.0.1", 60000)
        _, fake_socket, _ = run_main_with(
            [(_REQUEST, _CLIENT_ADDR), (_REQUEST, other_addr), OSError("stop")]
        )

        self.assertEqual(
            [c.args[1] for c in fake_socket.sendto.call_args_list],
            [_CLIENT_ADDR, other_addr],
        )

    def test_drops_malformed_packet_and_keeps_serving(self):
        malformed_packets = {
            "header_too_short": bytes(HEADER_SIZE - 1),
            "question_truncated": _REQUEST[:-1],
        }
        for case, packet in malformed_packets.items():
            with self.subTest(case=case):
                _, fake_socket, _ = run_main_with(
                    [(packet, _CLIENT_ADDR), (_REQUEST, _CLIENT_ADDR), OSError("stop")]
                )

                fake_socket.sendto.assert_called_once_with(
                    _EXPECTED_RESPONSE, _CLIENT_ADDR
                )

    def test_stops_and_logs_on_error(self):
        _, fake_socket, logger = run_main_with([OSError("boom")])

        logger.exception.assert_called_once()
        fake_socket.sendto.assert_not_called()


class TestMainWithResolver(unittest.TestCase):
    def run_with_lookup(self, lookup, recv_results):
        """以 --resolver 執行 main, ForwardingLookup 換成 `lookup`.

        回傳 (ForwardingLookup class mock, 假 socket, logger mock).
        """
        resolver_arg = f"{_RESOLVER_ADDR[0]}:{_RESOLVER_ADDR[1]}"
        with mock.patch.object(
            main_module, "ForwardingLookup", return_value=lookup
        ) as lookup_cls:
            _, fake_socket, logger = run_main_with(
                recv_results, ["--resolver", resolver_arg]
            )
        return lookup_cls, fake_socket, logger

    def test_replies_with_answers_from_resolver(self):
        answers = [a_record(_REQUEST_QUESTION.name, 1)]
        lookup_cls, fake_socket, _ = self.run_with_lookup(
            mock.Mock(return_value=answers),
            [(_REQUEST, _CLIENT_ADDR), OSError("stop")],
        )

        lookup_cls.assert_called_once_with(_RESOLVER_ADDR)
        fake_socket.sendto.assert_called_once_with(
            build_response(_REQUEST_HEADER, [_REQUEST_QUESTION], answers),
            _CLIENT_ADDR,
        )

    def test_drops_query_on_upstream_error_and_keeps_serving(self):
        lookup = mock.Mock(side_effect=[UpstreamError("timed out"), []])
        _, fake_socket, logger = self.run_with_lookup(
            lookup,
            [(_REQUEST, _CLIENT_ADDR), (_REQUEST, _CLIENT_ADDR), OSError("stop")],
        )

        logger.warning.assert_called_once()
        fake_socket.sendto.assert_called_once_with(
            build_response(_REQUEST_HEADER, [_REQUEST_QUESTION], []), _CLIENT_ADDR
        )


class TestParseAddress(unittest.TestCase):
    def test_splits_host_and_port(self):
        self.assertEqual(main_module.parse_address("127.0.0.1:5353"), _RESOLVER_ADDR)

    def test_rejects_invalid_address(self):
        for value in ("127.0.0.1", "127.0.0.1:", ":5353", "127.0.0.1:abc"):
            with (
                self.subTest(value=value),
                self.assertRaises(main_module.argparse.ArgumentTypeError),
            ):
                main_module.parse_address(value)


if __name__ == "__main__":
    unittest.main()
