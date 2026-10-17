import unittest
from unittest import mock

from app import main as main_module
from app.message.header import DNSHeader
from app.message.question import DNSQuestion
from app.request.parser import HEADER_SIZE
from app.response.builder import build_response

_CLIENT_ADDR = ("127.0.0.1", 54321)
_REQUEST_HEADER = DNSHeader(packet_identifier=1234, question_count=1)
_REQUEST_QUESTION = DNSQuestion(name="codecrafters.io")
_REQUEST = _REQUEST_HEADER.to_bytes() + _REQUEST_QUESTION.to_bytes()
_EXPECTED_RESPONSE = build_response(_REQUEST_HEADER, [_REQUEST_QUESTION])
# 高 2 bits 為 11 的 length byte, 代表 compression pointer
_COMPRESSION_POINTER_BYTE = 192


def run_main_with(recv_results):
    """用假 socket 執行 `main()`, `recvfrom` 依序回傳 `recv_results` 的每一項.

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
        main_module.main()
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

        expected = build_response(request_header, [question])
        fake_socket.sendto.assert_called_once_with(expected, _CLIENT_ADDR)

    def test_replies_to_compressed_questions_uncompressed(self):
        request_header = DNSHeader(packet_identifier=4321, question_count=2)
        first = DNSQuestion(name="codecrafters.io")
        # 第 2 個 question: "mail" 加上指向第 1 個 name (緊接在 header 之後) 的 pointer
        second_bytes = (
            b"\x04mail"
            + bytes([_COMPRESSION_POINTER_BYTE, HEADER_SIZE])
            + bytes([0, 1, 0, 1])
        )
        request = request_header.to_bytes() + first.to_bytes() + second_bytes
        _, fake_socket, _ = run_main_with([(request, _CLIENT_ADDR), OSError("stop")])

        expected = build_response(
            request_header, [first, DNSQuestion(name="mail.codecrafters.io")]
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


if __name__ == "__main__":
    unittest.main()
