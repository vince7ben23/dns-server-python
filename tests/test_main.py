import unittest
from unittest import mock

from app import main as main_module
from app.message.answer import DNSAnswer
from app.message.header import DNSHeader
from app.message.question import DNSQuestion

CLIENT_ADDR = ("127.0.0.1", 54321)


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

    def test_replies_to_client_with_header_question_and_answer(self):
        _, fake_socket = run_main_with([(b"query", CLIENT_ADDR), OSError("stop")])

        expected = (
            DNSHeader(
                packet_identifier=1234,
                query_response_indicator=1,
                question_count=1,
                answer_record_count=1,
            ).to_bytes()
            + DNSQuestion(name="codecrafters.io").to_bytes()
            + DNSAnswer(
                name="codecrafters.io", length=4, data=b"\x08\x08\x08\x08"
            ).to_bytes()
        )
        fake_socket.sendto.assert_called_once_with(expected, CLIENT_ADDR)

    def test_replies_to_each_request(self):
        other_addr = ("127.0.0.1", 60000)
        _, fake_socket = run_main_with(
            [(b"q1", CLIENT_ADDR), (b"q2", other_addr), OSError("stop")]
        )

        self.assertEqual(
            [c.args[1] for c in fake_socket.sendto.call_args_list],
            [CLIENT_ADDR, other_addr],
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
