from app.message.answer import DNSAnswer
from app.message.header import DNSHeader
from app.message.question import DNSQuestion

OPCODE_STANDARD_QUERY = 0
RCODE_NO_ERROR = 0
RCODE_NOT_IMPLEMENTED = 4
# 目前 answer 固定回 8.8.8.8
ANSWER_RDATA = bytes([8, 8, 8, 8])


def build_response(
    request_header: DNSHeader, request_questions: list[DNSQuestion]
) -> bytes:
    """依 request 的 header 與 questions 組出完整的 DNS response message.

    question 原樣帶回 (不壓縮), 並為每個 question 回一筆 A record.
    """
    if request_header.operation_code == OPCODE_STANDARD_QUERY:
        response_code = RCODE_NO_ERROR
    else:
        response_code = RCODE_NOT_IMPLEMENTED

    response_header = DNSHeader(
        packet_identifier=request_header.packet_identifier,
        query_response_indicator=1,
        operation_code=request_header.operation_code,
        recursion_desired=request_header.recursion_desired,
        response_code=response_code,
        question_count=len(request_questions),
        answer_record_count=len(request_questions),
    )

    response_answers = [
        DNSAnswer(
            name=question.name,
            rdata_length=len(ANSWER_RDATA),
            rdata=ANSWER_RDATA,
        )
        for question in request_questions
    ]
    return (
        response_header.to_bytes()
        + b"".join(question.to_bytes() for question in request_questions)
        + b"".join(answer.to_bytes() for answer in response_answers)
    )
