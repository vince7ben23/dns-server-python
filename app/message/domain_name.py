# 單一 label 長度上限 (length byte 的高 2 bits 保留給 compression pointer)
_MAX_LABEL_LENGTH = 63
# 整個 domain name 編碼後的長度上限 (含 length bytes 與結尾的 null byte)
_MAX_NAME_LENGTH = 255


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
    """從 offset 開始解析 label 序列, 回傳 (name, 結尾 null byte 之後的 offset)."""
    start = offset
    labels = []
    while True:
        if offset >= len(data):
            raise ValueError("domain name is missing its null terminator")
        length = data[offset]
        offset += 1
        if length == 0:
            break
        # 高 2 bits 非 0 代表 compression pointer 或保留值, 目前不支援
        if length > _MAX_LABEL_LENGTH:
            raise ValueError(f"unsupported label length byte {length}")
        if offset + length > len(data):
            raise ValueError("label content exceeds data length")
        try:
            labels.append(data[offset : offset + length].decode("ascii"))
        except UnicodeDecodeError:
            raise ValueError("label must be ASCII") from None
        offset += length
        if offset - start >= _MAX_NAME_LENGTH:
            # 還沒讀到 null byte 就已達上限, 加上 null byte 必定超過
            raise ValueError(f"encoded name exceeds {_MAX_NAME_LENGTH} bytes")
    return ".".join(labels), offset
