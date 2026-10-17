from app.message.answer import DNSAnswer
from app.message.header import DNSHeader
from app.message.question import DNSQuestion

OPCODE_STANDARD_QUERY = 0
RCODE_NO_ERROR = 0
RCODE_NOT_IMPLEMENTED = 4
# 目前 answer 固定回 8.8.8.8
ANSWER_RDATA = bytes([8, 8, 8, 8])


def build_response(request_header: DNSHeader, request_question: DNSQuestion) -> bytes:
    """依 request 的 header 與 question 組出完整的 DNS response message."""
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
        question_count=1,
        answer_record_count=1,
    )

    response_answer = DNSAnswer(
        name=request_question.name, rdata_length=4, rdata=b"\x08\x08\x08\x08"
    )
    return (
        response_header.to_bytes()
        + request_question.to_bytes()
        + response_answer.to_bytes()
    )
