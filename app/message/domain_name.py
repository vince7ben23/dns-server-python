# 單一 label 長度上限（length byte 的高 2 bits 保留給 compression pointer）
_MAX_LABEL_LENGTH = 63
# 整個 domain name 編碼後的長度上限（含 length bytes 與結尾的 null byte）
_MAX_NAME_LENGTH = 255


def encode_domain_name(name: str) -> bytes:
    """將 domain name 編碼為 label 序列：<length><content>...\\x00。"""
    # root domain（"" 或 "."）沒有任何 label；FQDN 結尾的 "." 忽略
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
