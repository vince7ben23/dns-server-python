import socket

from app.message.answer import DNSAnswer
from app.message.header import DNSHeader
from app.message.parser import parse_answers, parse_header, parse_questions
from app.message.question import DNSQuestion

# UDP DNS message 的大小上限
_MAX_MESSAGE_SIZE = 512
# 轉送用的 query ID; 每次查詢用新的 socket 且只收一個 reply, 不需靠 ID 配對.
# client 的 ID 由 server 端從 request header 放回 response
_QUERY_ID = 0


class UpstreamError(Exception):
    """上游 resolver 沒回應或回應無法使用.

    刻意不繼承 OSError / ValueError, 讓 main 能和 socket 錯誤及壞的 client 封包區分.
    """


def build_query(packet_id: int, question: DNSQuestion, recursion_desired: int) -> bytes:
    """組出只含一個 question 的 query (resolver 只回應單一 question 的封包)."""
    header = DNSHeader(
        packet_identifier=packet_id,
        recursion_desired=recursion_desired,
        question_count=1,
    )
    return header.to_bytes() + question.to_bytes()


def parse_reply(reply: bytes) -> list[DNSAnswer]:
    """從 resolver 的 reply 取出 answers; 格式錯誤或不是 response 時 raise ValueError."""
    header = parse_header(reply)
    if header.query_response_indicator != 1:
        raise ValueError("reply is not a response")
    _, offset = parse_questions(reply, header.question_count)
    answers, _ = parse_answers(reply, header.answer_record_count, offset)
    return answers


class ForwardingLookup:
    """把每個 question 轉送給上游 resolver, 符合 server.handler.Lookup."""

    def __init__(self, address: tuple[str, int], timeout: float = 2.0):
        self.address = address
        self.timeout = timeout

    def __call__(self, question: DNSQuestion) -> list[DNSAnswer]:
        query = build_query(_QUERY_ID, question, recursion_desired=1)
        try:
            # 每次查詢用新的 socket, 避免讀到前一次逾時後才到的 reply
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream:
                upstream.settimeout(self.timeout)
                upstream.sendto(query, self.address)
                reply, _ = upstream.recvfrom(_MAX_MESSAGE_SIZE)
            return parse_reply(reply)
        except (OSError, ValueError) as e:
            raise UpstreamError(
                f"{self.address} failed for {question.name}: {e}"
            ) from e
