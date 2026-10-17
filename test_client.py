#!/usr/bin/env python3
"""送 UDP 封包給本機 DNS server 並印出回應的小工具.

用法:
    python3 test_client.py                 # 送預設封包到 127.0.0.1:2053
    python3 test_client.py --host 127.0.0.1 --port 2053
    python3 test_client.py --message hello # 自訂 payload 內容
"""

import argparse
import socket


def main():
    parser = argparse.ArgumentParser(
        description="Send a UDP packet to the DNS server and print the response"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="server address (default 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=2053, help="server port (default 2053)"
    )
    parser.add_argument("--message", default="hello", help="payload string to send")
    parser.add_argument(
        "--timeout", type=float, default=3.0, help="seconds to wait for a response"
    )
    args = parser.parse_args()

    # 前 2 bytes 假裝是 DNS 的 transaction ID, 後面接自訂訊息
    payload = b"\x12\x34" + args.message.encode()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(args.timeout)
    try:
        sock.sendto(payload, (args.host, args.port))
        print(f"Sent {len(payload)} bytes to {args.host}:{args.port} -> {payload!r}")

        data, addr = sock.recvfrom(512)
        print(f"Received response from {addr}, length {len(data)}: {data!r}")
    except TimeoutError:
        print("Timeout: no response received (server may be down, or not replying yet)")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
