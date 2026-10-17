import unittest
from unittest import mock

from app import main as main_module
from app.message.header import DNSHeader
from app.message.question import DNSQuestion
from app.request.parser import HEADER_SIZE
from app.response.builder import build_response

CLIENT_ADDR = ("127.0.0.1", 54321)
REQUEST_HEADER = DNSHeader(packet_identifier=1234, question_count=1)
REQUEST_QUESTION = DNSQuestion(name="codecrafters.io")
REQUEST = REQUEST_HEADER.to_bytes() + REQUEST_QUESTION.to_bytes()
EXPECTED_RESPONSE = build_response(REQUEST_HEADER, REQUEST_QUESTION)


def run_main_with(recv_results):
    """Run `main()` against a fake socket whose `recvfrom` yields `recv_results` in order.

    `main()` loops forever, so the last item should be an exception to break out.
    """
    fake_socket = mock.Mock()
    fake_socket.recvfrom.side_effect = recv_results
    with (
        mock.patch.object(
            main_module.socket, "socket", return_value=fake_socket
        ) as socket_cls,
        mock.patch.object(main_module, "logger"),
    ):
        main_module.main()
    return socket_cls, fake_socket


class TestMain(unittest.TestCase):
    def test_binds_udp_socket_on_port_2053(self):
        socket_cls, fake_socket = run_main_with([OSError("stop")])

        socket_cls.assert_called_once_with(
            main_module.socket.AF_INET, main_module.socket.SOCK_DGRAM
        )
        fake_socket.bind.assert_called_once_with(("127.0.0.1", 2053))

    def test_replies_with_response_built_from_request(self):
        request_header = DNSHeader(
            packet_identifier=4321, recursion_desired=1, question_count=1
        )
        question = DNSQuestion(name="example.com")
        _, fake_socket = run_main_with(
            [
                (request_header.to_bytes() + question.to_bytes(), CLIENT_ADDR),
                OSError("stop"),
            ]
        )

        expected = build_response(request_header, question)
        fake_socket.sendto.assert_called_once_with(expected, CLIENT_ADDR)

    def test_replies_to_each_request(self):
        other_addr = ("127.0.0.1", 60000)
        _, fake_socket = run_main_with(
            [(REQUEST, CLIENT_ADDR), (REQUEST, other_addr), OSError("stop")]
        )

        self.assertEqual(
            [c.args[1] for c in fake_socket.sendto.call_args_list],
            [CLIENT_ADDR, other_addr],
        )

    def test_drops_malformed_packet_and_keeps_serving(self):
        malformed_packets = {
            "header_too_short": bytes(HEADER_SIZE - 1),
            "question_truncated": REQUEST[:-1],
        }
        for case, packet in malformed_packets.items():
            with self.subTest(case=case):
                _, fake_socket = run_main_with(
                    [(packet, CLIENT_ADDR), (REQUEST, CLIENT_ADDR), OSError("stop")]
                )

                fake_socket.sendto.assert_called_once_with(
                    EXPECTED_RESPONSE, CLIENT_ADDR
                )

    def test_stops_and_logs_on_error(self):
        fake_socket = mock.Mock()
        fake_socket.recvfrom.side_effect = OSError("boom")
        with (
            mock.patch.object(main_module.socket, "socket", return_value=fake_socket),
            mock.patch.object(main_module, "logger") as logger,
        ):
            main_module.main()

        logger.exception.assert_called_once()
        fake_socket.sendto.assert_not_called()


if __name__ == "__main__":
    unittest.main()
