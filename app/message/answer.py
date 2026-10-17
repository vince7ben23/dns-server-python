import struct
from dataclasses import dataclass

from app.message.domain_name import encode_domain_name

# 各欄位的 bit 寬度，用於驗證數值範圍
_FIELD_BITS = {
    "record_type": 16,
    "record_class": 16,
    "ttl": 32,
    "length": 16,
}


@dataclass
class DNSAnswer:
    """DNS answer section RR: Name + Type(2) + Class(2) + TTL(4) + RDLENGTH(2) + RDATA。"""

    name: str
    length: int  # RDLENGTH，須等於 len(data)
    data: bytes  # RDATA；A record 為 4-byte IPv4 address
    record_type: int = 1  # 1 = A record
    record_class: int = 1  # 1 = IN
    ttl: int = 60

    def __post_init__(self):
        for field_name, bits in _FIELD_BITS.items():
            value = getattr(self, field_name)
            if not 0 <= value < (1 << bits):
                raise ValueError(f"{field_name}={value} does not fit in {bits} bits")
        if self.length != len(self.data):
            raise ValueError(
                f"length={self.length} does not match data length {len(self.data)}"
            )

    def to_bytes(self) -> bytes:
        return (
            encode_domain_name(self.name)
            + struct.pack(
                "!2HIH",  # type(16) class(16) ttl(32) rdlength(16), big-endian
                self.record_type,
                self.record_class,
                self.ttl,
                self.length,
            )
            + self.data
        )
