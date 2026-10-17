import struct

from app.message.domain_name import decode_domain_name
from app.message.header import DNSHeader
from app.message.question import DNSQuestion

# DNS header 固定 12 bytes
HEADER_SIZE = 12
# question 在 name 之後的固定長度: type(2) + class(2)
QUESTION_TYPE_CLASS_SIZE = 4


def parse_header(request: bytes) -> DNSHeader:
    """從 DNS request 開頭的 12 bytes 解析出 header, 之後的資料忽略."""
    if len(request) < HEADER_SIZE:
        raise ValueError(f"header needs {HEADER_SIZE} bytes, got {len(request)}")

    (
        packet_identifier,
        flags,
        question_count,
        answer_record_count,
        authority_record_count,
        additional_record_count,
    ) = struct.unpack("!6H", request[:HEADER_SIZE])

    # flags: QR(1) OPCODE(4) AA(1) TC(1) RD(1) | RA(1) Z(3) RCODE(4)
    # 位移量與 DNSHeader.to_bytes 對稱, 右移後用 mask 取出該欄位的 bit 寬度
    return DNSHeader(
        packet_identifier=packet_identifier,
        query_response_indicator=(flags >> 15) & 0b1,
        operation_code=(flags >> 11) & 0b1111,
        authoritative_answer=(flags >> 10) & 0b1,
        truncation=(flags >> 9) & 0b1,
        recursion_desired=(flags >> 8) & 0b1,
        recursion_available=(flags >> 7) & 0b1,
        reserved=(flags >> 4) & 0b111,
        response_code=flags & 0b1111,
        question_count=question_count,
        answer_record_count=answer_record_count,
        authority_record_count=authority_record_count,
        additional_record_count=additional_record_count,
    )


def parse_question(
    request: bytes, offset: int = HEADER_SIZE
) -> tuple[DNSQuestion, int]:
    """從 offset 解析一個 question, 回傳 (question, 下一個 section 的 offset)."""
    name, offset = decode_domain_name(request, offset)
    if offset + QUESTION_TYPE_CLASS_SIZE > len(request):
        raise ValueError(
            f"question type and class need {QUESTION_TYPE_CLASS_SIZE} bytes, "
            f"got {len(request) - offset}"
        )
    record_type, record_class = struct.unpack_from("!2H", request, offset)
    question = DNSQuestion(
        name=name, record_type=record_type, record_class=record_class
    )
    return question, offset + QUESTION_TYPE_CLASS_SIZE
