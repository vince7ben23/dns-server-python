import argparse
import socket

from app.client.forward import ForwardingLookup, UpstreamError
from app.libs.logger import logger
from app.server.handler import Lookup, fixed_lookup, handle_query


def parse_address(value: str) -> tuple[str, int]:
    """把 "ip:port" 拆成 (ip, port)."""
    host, separator, port = value.rpartition(":")
    if not separator or not host or not port.isdigit():
        raise argparse.ArgumentTypeError(f"expected <ip>:<port>, got {value!r}")
    return host, int(port)


def main(argv: list[str] | None = None):
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--resolver",
        type=parse_address,
        help="轉送 query 的上游 resolver, 格式 <ip>:<port>; 未指定時固定回 8.8.8.8",
    )
    args = arg_parser.parse_args(argv)
    lookup: Lookup = ForwardingLookup(args.resolver) if args.resolver else fixed_lookup

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("127.0.0.1", 2053))

    while True:
        try:
            buf, client_addr = udp_socket.recvfrom(512)
            logger.debug("Received %d bytes from %s: %r", len(buf), client_addr, buf)
            try:
                response = handle_query(buf, lookup)
            except ValueError as e:
                # 壞封包只略過, 不讓 server 停掉
                logger.warning("Dropping malformed packet from %s: %s", client_addr, e)
                continue
            except UpstreamError as e:
                # 上游查不到就不回應, 讓 client 自行逾時重試
                logger.warning("Dropping query from %s: %s", client_addr, e)
                continue

            udp_socket.sendto(response, client_addr)
        except Exception as e:
            # 壞封包以外的錯誤 (socket 錯誤, 程式 bug 等) 無法恢復, 記錄後停止 server
            logger.exception("Unexpected error, stopping server: %s", e)
            break


if __name__ == "__main__":
    main()
