import struct
from dataclasses import dataclass

from app.message.domain_name import encode_domain_name

# record_type 與 record_class 皆為 2-byte unsigned int
_MAX_UINT16 = 0xFFFF


@dataclass
class DNSQuestion:
    """DNS question section: Name + Type(2 bytes) + Class(2 bytes)."""

    name: str
    record_type: int = 1  # 1 = A record
    record_class: int = 1  # 1 = IN

    def __post_init__(self):
        for field_name in ("record_type", "record_class"):
            value = getattr(self, field_name)
            if not 0 <= value <= _MAX_UINT16:
                raise ValueError(f"{field_name}={value} does not fit in 16 bits")

    def to_bytes(self) -> bytes:
        return encode_domain_name(self.name) + struct.pack(
            "!2H",  # 2 unsigned short (16-bit) integers, big-endian
            self.record_type,
            self.record_class,
        )
