import struct

from app.message.answer import ANSWER_FIXED_FIELDS_SIZE, DNSAnswer
from app.message.domain_name import decode_domain_name
from app.message.header import HEADER_SIZE, DNSHeader
from app.message.question import QUESTION_TYPE_CLASS_SIZE, DNSQuestion


def parse_header(message: bytes) -> DNSHeader:
    """從 DNS message 開頭的 12 bytes 解析出 header, 之後的資料忽略."""
    if len(message) < HEADER_SIZE:
        raise ValueError(f"header needs {HEADER_SIZE} bytes, got {len(message)}")

    (
        packet_identifier,
        flags,
        question_count,
        answer_record_count,
        authority_record_count,
        additional_record_count,
    ) = struct.unpack("!6H", message[:HEADER_SIZE])

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
    message: bytes, offset: int = HEADER_SIZE
) -> tuple[DNSQuestion, int]:
    """從 offset 解析一個 question, 回傳 (question, 下一個 section 的 offset)."""
    name, offset = decode_domain_name(message, offset)
    if offset + QUESTION_TYPE_CLASS_SIZE > len(message):
        raise ValueError(
            f"question type and class need {QUESTION_TYPE_CLASS_SIZE} bytes, "
            f"got {len(message) - offset}"
        )
    record_type, record_class = struct.unpack_from("!2H", message, offset)
    question = DNSQuestion(
        name=name, record_type=record_type, record_class=record_class
    )
    return question, offset + QUESTION_TYPE_CLASS_SIZE


def parse_questions(
    message: bytes, count: int, offset: int = HEADER_SIZE
) -> tuple[list[DNSQuestion], int]:
    """從 offset 依序解析 count 個 question.

    回傳 (questions, 下一個 section 的 offset).
    """
    questions = []
    for _ in range(count):
        question, offset = parse_question(message, offset)
        questions.append(question)
    return questions, offset


def parse_answer(message: bytes, offset: int) -> tuple[DNSAnswer, int]:
    """從 offset 解析一個 answer RR, 回傳 (answer, 下一筆 RR 的 offset)."""
    name, offset = decode_domain_name(message, offset)
    if offset + ANSWER_FIXED_FIELDS_SIZE > len(message):
        raise ValueError(
            f"answer fixed fields need {ANSWER_FIXED_FIELDS_SIZE} bytes, "
            f"got {len(message) - offset}"
        )
    record_type, record_class, ttl, rdata_length = struct.unpack_from(
        "!2HIH", message, offset
    )
    offset += ANSWER_FIXED_FIELDS_SIZE
    if offset + rdata_length > len(message):
        raise ValueError(
            f"rdata needs {rdata_length} bytes, got {len(message) - offset}"
        )
    answer = DNSAnswer(
        name=name,
        rdata_length=rdata_length,
        rdata=message[offset : offset + rdata_length],
        record_type=record_type,
        record_class=record_class,
        ttl=ttl,
    )
    return answer, offset + rdata_length


def parse_answers(
    message: bytes, count: int, offset: int
) -> tuple[list[DNSAnswer], int]:
    """從 offset 依序解析 count 個 answer RR.

    回傳 (answers, 下一個 section 的 offset).
    """
    answers = []
    for _ in range(count):
        answer, offset = parse_answer(message, offset)
        answers.append(answer)
    return answers, offset
