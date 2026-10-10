import socket

from app.libs.logger import logger
from app.message.header import DNSHeader


def main():

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("127.0.0.1", 2053))

    while True:
        try:
            buf, source = udp_socket.recvfrom(512)
            logger.debug("Received %d bytes from %s: %r", len(buf), source, buf)
            response = DNSHeader(
                packet_identifier=1234, query_response_indicator=1
            ).to_bytes()

            udp_socket.sendto(response, source)
        except Exception as e:
            logger.exception("Error receiving data: %s", e)
            break


if __name__ == "__main__":
    main()
