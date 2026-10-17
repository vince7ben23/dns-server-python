import unittest

from app.message.domain_name import decode_domain_name, encode_domain_name

# 高 2 bits 為 11 的 length byte, 代表 compression pointer
_COMPRESSION_POINTER_BYTE = 192


class TestEncodeDomainName(unittest.TestCase):
    def test_encodes_labels_with_length_prefix_and_null_terminator(self):
        self.assertEqual(encode_domain_name("google.com"), b"\x06google\x03com\x00")

    def test_root_domain_is_single_null_byte(self):
        self.assertEqual(encode_domain_name(""), b"\x00")
        self.assertEqual(encode_domain_name("."), b"\x00")

    def test_trailing_dot_is_ignored(self):
        self.assertEqual(
            encode_domain_name("google.com."), encode_domain_name("google.com")
        )

    def test_rejects_empty_label(self):
        for name in ("google..com", ".com", "google.com.."):
            with self.subTest(name=name), self.assertRaises(ValueError):
                encode_domain_name(name)

    def test_accepts_label_of_63_bytes(self):
        self.assertEqual(encode_domain_name("a" * 63), b"\x3f" + b"a" * 63 + b"\x00")

    def test_rejects_label_longer_than_63_bytes(self):
        with self.assertRaises(ValueError):
            encode_domain_name("a" * 64 + ".com")

    def test_accepts_name_of_255_encoded_bytes(self):
        # 3 * (1 + 63) + (1 + 61) + 1 = 255
        name = ".".join(["a" * 63] * 3 + ["b" * 61])
        self.assertEqual(len(encode_domain_name(name)), 255)

    def test_rejects_name_longer_than_255_encoded_bytes(self):
        name = ".".join(["a" * 63] * 3 + ["b" * 62])
        with self.assertRaises(ValueError):
            encode_domain_name(name)

    def test_rejects_non_ascii_label(self):
        with self.assertRaisesRegex(ValueError, "must be ASCII"):
            encode_domain_name("例子.com")


class TestDecodeDomainName(unittest.TestCase):
    def test_decodes_labels_and_returns_offset_after_null_byte(self):
        self.assertEqual(
            decode_domain_name(b"\x06google\x03com\x00", 0), ("google.com", 12)
        )

    def test_starts_from_offset_and_ignores_trailing_data(self):
        prefix_len = 3
        data = bytes(prefix_len) + b"\x01a\x00" + bytes([0, 1])
        self.assertEqual(decode_domain_name(data, prefix_len), ("a", prefix_len + 3))

    def test_root_domain(self):
        self.assertEqual(decode_domain_name(b"\x00", 0), ("", 1))

    def test_round_trip_with_encode(self):
        name = "codecrafters.io"
        encoded = encode_domain_name(name)
        self.assertEqual(decode_domain_name(encoded, 0), (name, len(encoded)))

    def test_accepts_name_of_255_encoded_bytes(self):
        name = ".".join(["a" * 63] * 3 + ["b" * 61])
        self.assertEqual(decode_domain_name(encode_domain_name(name), 0), (name, 255))

    def test_rejects_name_longer_than_255_encoded_bytes(self):
        # 4 個 63-byte label 共 256 bytes, 尚未加上 null byte
        data = (bytes([63]) + b"a" * 63) * 4 + b"\x00"
        with self.assertRaisesRegex(ValueError, "exceeds"):
            decode_domain_name(data, 0)

    def test_rejects_truncated_data(self):
        for data in (b"", b"\x01a", b"\x03ab"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                decode_domain_name(data, 0)

    def test_rejects_compression_pointer(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            decode_domain_name(bytes([_COMPRESSION_POINTER_BYTE, 12]), 0)

    def test_rejects_non_ascii_label(self):
        with self.assertRaisesRegex(ValueError, "must be ASCII"):
            decode_domain_name(bytes([1, 200, 0]), 0)


if __name__ == "__main__":
    unittest.main()
