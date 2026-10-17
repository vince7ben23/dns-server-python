import struct

from app.message.header import DNSHeader

# DNS header 固定 12 bytes
HEADER_SIZE = 12


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
