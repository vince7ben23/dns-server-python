import socket

from app.libs.logger import logger
from app.message.answer import DNSAnswer
from app.message.header import DNSHeader
from app.message.question import DNSQuestion


def main():

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("127.0.0.1", 2053))

    while True:
        try:
            buf, client_addr = udp_socket.recvfrom(512)
            logger.debug("Received %d bytes from %s: %r", len(buf), client_addr, buf)
            question = DNSQuestion(name="codecrafters.io")
            answer = DNSAnswer(
                name="codecrafters.io", rdata_length=4, rdata=b"\x08\x08\x08\x08"
            )
            header = DNSHeader(
                packet_identifier=1234,
                query_response_indicator=1,
                question_count=1,
                answer_record_count=1,
            )
            response = header.to_bytes() + question.to_bytes() + answer.to_bytes()

            udp_socket.sendto(response, client_addr)
        except Exception as e:
            logger.exception("Error receiving data: %s", e)
            break


if __name__ == "__main__":
    main()
