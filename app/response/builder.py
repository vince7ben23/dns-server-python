from app.message.answer import DNSAnswer
from app.message.header import DNSHeader
from app.message.question import DNSQuestion

_OPCODE_STANDARD_QUERY = 0
_RCODE_NO_ERROR = 0
_RCODE_NOT_IMPLEMENTED = 4


def build_response(request_header: DNSHeader) -> bytes:
    """依 request header 組出完整的 DNS response message."""
    if request_header.operation_code == _OPCODE_STANDARD_QUERY:
        response_code = _RCODE_NO_ERROR
    else:
        response_code = _RCODE_NOT_IMPLEMENTED

    header = DNSHeader(
        packet_identifier=request_header.packet_identifier,
        query_response_indicator=1,
        operation_code=request_header.operation_code,
        recursion_desired=request_header.recursion_desired,
        response_code=response_code,
        question_count=1,
        answer_record_count=1,
    )
    question = DNSQuestion(name="codecrafters.io")
    answer = DNSAnswer(
        name="codecrafters.io", rdata_length=4, rdata=b"\x08\x08\x08\x08"
    )
    return header.to_bytes() + question.to_bytes() + answer.to_bytes()
