import socket

from app.libs.logger import logger
from app.message.parser import parse_header, parse_questions
from app.server.response import build_response


def main():
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("127.0.0.1", 2053))

    while True:
        try:
            buf, client_addr = udp_socket.recvfrom(512)
            logger.debug("Received %d bytes from %s: %r", len(buf), client_addr, buf)
            try:
                request_header = parse_header(buf)
                questions, _ = parse_questions(buf, request_header.question_count)
            except ValueError as e:
                # 壞封包只略過, 不讓 server 停掉
                logger.warning("Dropping malformed packet from %s: %s", client_addr, e)
                continue

            response = build_response(request_header, questions)
            udp_socket.sendto(response, client_addr)
        except Exception as e:
            # 壞封包以外的錯誤 (socket 錯誤, 程式 bug 等) 無法恢復, 記錄後停止 server
            logger.exception("Unexpected error, stopping server: %s", e)
            break


if __name__ == "__main__":
    main()
