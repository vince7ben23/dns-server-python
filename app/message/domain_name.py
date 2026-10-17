# 單一 label 長度上限 (length byte 的高 2 bits 保留給 compression pointer)
_MAX_LABEL_LENGTH = 63
# 整個 domain name 編碼後的長度上限 (含 length bytes 與結尾的 null byte)
_MAX_NAME_LENGTH = 255
# 高 2 bits 為 11 的 length byte 代表 compression pointer, 低 14 bits 為目標 offset
_POINTER_FLAG = 0b11000000
_POINTER_SIZE = 2


def encode_domain_name(name: str) -> bytes:
    """將 domain name 編碼為 label 序列: <length><content>...\\x00."""
    # root domain ("" 或 ".") 沒有任何 label; FQDN 結尾的 "." 忽略
    labels = name.removesuffix(".").split(".") if name not in ("", ".") else []
    encoded = bytearray()
    for label in labels:
        try:
            raw = label.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError(f"label {label!r} must be ASCII") from None
        if not 0 < len(raw) <= _MAX_LABEL_LENGTH:
            raise ValueError(
                f"label {label!r} length must be 1..{_MAX_LABEL_LENGTH} bytes"
            )
        encoded += bytes([len(raw)]) + raw
    encoded += b"\x00"  # null byte 作為 domain name 結尾
    if len(encoded) > _MAX_NAME_LENGTH:
        raise ValueError(f"encoded name exceeds {_MAX_NAME_LENGTH} bytes")
    return bytes(encoded)


def decode_domain_name(data: bytes, offset: int) -> tuple[str, int]:
    """從 offset 開始解析 label 序列, 回傳 (name, 此 name 在原位置結尾之後的 offset).

    支援 compression pointer: 遇到 pointer 時跳到它指向的 offset 繼續讀,
    回傳的 offset 則是第一個 pointer 的 2 bytes 之後.
    """
    labels = []
    encoded_length = 0  # 展開後的 name 長度, 不含 pointer 本身
    end_offset = None  # 遇到第一個 pointer 後, name 在原位置的結尾
    while True:
        if offset >= len(data):
            raise ValueError("domain name is missing its null terminator")
        length = data[offset]
        if (length & _POINTER_FLAG) == _POINTER_FLAG:
            if offset + _POINTER_SIZE > len(data):
                raise ValueError("compression pointer is truncated")
            # 去掉高 2 bits 後, 與下一個 byte 組成 14-bit 的目標 offset
            target = ((length & ~_POINTER_FLAG) << 8) | data[offset + 1]
            # 只允許往前指, 每次跳躍 offset 嚴格遞減, 避免 pointer 形成迴圈
            if target >= offset:
                raise ValueError("compression pointer must point backwards")
            if end_offset is None:
                end_offset = offset + _POINTER_SIZE
            offset = target
            continue
        offset += 1
        if length == 0:
            break
        # 高 2 bits 為 01 或 10 是保留值
        if length > _MAX_LABEL_LENGTH:
            raise ValueError(f"unsupported label length byte {length}")
        if offset + length > len(data):
            raise ValueError("label content exceeds data length")
        try:
            labels.append(data[offset : offset + length].decode("ascii"))
        except UnicodeDecodeError:
            raise ValueError("label must be ASCII") from None
        offset += length
        encoded_length += 1 + length
        if encoded_length >= _MAX_NAME_LENGTH:
            # 還沒讀到 null byte 就已達上限, 加上 null byte 必定超過
            raise ValueError(f"encoded name exceeds {_MAX_NAME_LENGTH} bytes")
    return ".".join(labels), offset if end_offset is None else end_offset
