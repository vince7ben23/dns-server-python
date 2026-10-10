import struct
from dataclasses import dataclass, fields

# 每個欄位的 bit 寬度，用於驗證數值範圍
_FIELD_BITS = {
    "packet_identifier": 16,
    "query_response_indicator": 1,
    "operation_code": 4,
    "authoritative_answer": 1,
    "truncation": 1,
    "recursion_desired": 1,
    "recursion_available": 1,
    "reserved": 3,
    "response_code": 4,
    "question_count": 16,
    "answer_record_count": 16,
    "authority_record_count": 16,
    "additional_record_count": 16,
}


@dataclass
class DNSHeader:
    """DNS message header (12 bytes, big-endian)。"""

    packet_identifier: int = 0
    query_response_indicator: int = 0
    operation_code: int = 0
    authoritative_answer: int = 0
    truncation: int = 0
    recursion_desired: int = 0
    recursion_available: int = 0
    reserved: int = 0
    response_code: int = 0
    question_count: int = 0
    answer_record_count: int = 0
    authority_record_count: int = 0
    additional_record_count: int = 0

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            bits = _FIELD_BITS[field.name]
            if not 0 <= value < (1 << bits):
                raise ValueError(f"{field.name}={value} does not fit in {bits} bits")

    def to_bytes(self) -> bytes:
        # flags: QR(1) OPCODE(4) AA(1) TC(1) RD(1) | RA(1) Z(3) RCODE(4)
        flags = (
            (
                self.query_response_indicator << 15
            )  # 1 bits, 第一位移動到第十六位 => 左移 15 bits
            | (
                self.operation_code << 11
            )  # 4 bits, (第一位, 第四位) 移動 (第十二位, 第十五位) => 左移 11 bits
            | (
                self.authoritative_answer << 10
            )  # 1 bits, 第一位移動到第十一位 => 左移 10 bits
            | (self.truncation << 9)
            | (self.recursion_desired << 8)
            | (self.recursion_available << 7)
            | (self.reserved << 4)
            | self.response_code
        )
        return struct.pack(
            "!6H",  # 6 unsigned short (16-bit) integers in network byte order, big-endian
            self.packet_identifier,
            flags,
            self.question_count,
            self.answer_record_count,
            self.authority_record_count,
            self.additional_record_count,
        )
