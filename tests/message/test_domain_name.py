import unittest

from app.message.domain_name import encode_domain_name


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


if __name__ == "__main__":
    unittest.main()
