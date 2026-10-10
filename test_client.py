#!/usr/bin/env python3
"""A simple UDP test client for poking the local DNS server.

Usage:
    python3 test_client.py                 # send default packet to 127.0.0.1:2053
    python3 test_client.py --host 127.0.0.1 --port 2053
    python3 test_client.py --message hello # customize the payload content
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

    # The first two bytes pretend to be a DNS transaction ID, followed by the custom message.
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
