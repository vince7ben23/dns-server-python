"""多個測試共用的常數與 helper; 不是測試模組, 不對應 app/ 的任何模組."""

from app.message.answer import DNSAnswer

# 高 2 bits 為 11 的 length byte, 代表 compression pointer
COMPRESSION_POINTER_BYTE = 192
# 16-bit 欄位可容納的最小溢位值
UINT16_OVERFLOW = 1 << 16
# 32-bit 欄位可容納的最小溢位值
UINT32_OVERFLOW = 1 << 32


def a_record(name: str, last_octet: int) -> DNSAnswer:
    """組出 name 的 A record, RDATA 為 10.0.0.<last_octet>."""
    rdata = bytes([10, 0, 0, last_octet])
    return DNSAnswer(name=name, rdata_length=len(rdata), rdata=rdata)
