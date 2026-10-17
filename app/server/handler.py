from collections.abc import Callable

from app.message.answer import DNSAnswer
from app.message.parser import parse_header, parse_questions
from app.message.question import DNSQuestion
from app.server.response import OPCODE_STANDARD_QUERY, build_response

# 依單一 question 查出 answers 的函式, 由 main 決定用哪一個實作
Lookup = Callable[[DNSQuestion], list[DNSAnswer]]

# fixed_lookup 固定回 8.8.8.8
_FIXED_RDATA = bytes([8, 8, 8, 8])


def fixed_lookup(question: DNSQuestion) -> list[DNSAnswer]:
    """不查任何上游, 為 question 回一筆固定的 A record."""
    return [
        DNSAnswer(
            name=question.name, rdata_length=len(_FIXED_RDATA), rdata=_FIXED_RDATA
        )
    ]


def handle_query(request: bytes, lookup: Lookup) -> bytes:
    """解析 request, 逐一 lookup 每個 question, 合併 answers 後組出 response.

    request 格式錯誤時 raise ValueError. 非 standard query 不 lookup, 不回 answer.
    """
    request_header = parse_header(request)
    questions, _ = parse_questions(request, request_header.question_count)

    answers = []
    if request_header.operation_code == OPCODE_STANDARD_QUERY:
        for question in questions:
            answers += lookup(question)
    return build_response(request_header, questions, answers)
