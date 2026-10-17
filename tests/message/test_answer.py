import unittest

from app.message.answer import DNSAnswer

# 16-bit 欄位可容納的最小溢位值
_UINT16_OVERFLOW = 1 << 16
# 32-bit 欄位可容納的最小溢位值
_UINT32_OVERFLOW = 1 << 32


class TestDNSAnswerToBytes(unittest.TestCase):
    def test_stage_expected_answer(self):
        answer = DNSAnswer(name="codecrafters.io", length=4, data=bytes([8, 8, 8, 8]))
        self.assertEqual(
            answer.to_bytes(),
            b"\x0ccodecrafters\x02io\x00"  # name
            + bytes([0, 1])  # type: A
            + bytes([0, 1])  # class: IN
            + bytes([0, 0, 0, 60])  # TTL: 60
            + bytes([0, 4])  # RDLENGTH: 4
            + bytes([8, 8, 8, 8]),  # RDATA: 8.8.8.8
        )

    def test_fixed_fields_are_big_endian(self):
        # 用 16 進位讓每個 byte 都不同, 方便直接對照輸出的 byte 順序
        answer = DNSAnswer(
            name="a",
            length=2,
            data=b"\xaa\xbb",
            record_type=5,
            record_class=0x0102,
            ttl=0x01020304,
        )
        # name="a" 編碼後的長度: \x01 a \x00
        name_len = 3
        self.assertEqual(
            answer.to_bytes()[name_len:],
            bytes([0, 5])  # type: 5
            + b"\x01\x02"  # class: 0x0102
            + b"\x01\x02\x03\x04"  # TTL: 0x01020304
            + bytes([0, 2])  # RDLENGTH: 2
            + b"\xaa\xbb",  # RDATA
        )


class TestDNSAnswerValidation(unittest.TestCase):
    def test_rejects_field_overflow(self):
        cases = [
            {"record_type": _UINT16_OVERFLOW},
            {"record_class": -1},
            {"ttl": _UINT32_OVERFLOW},
            {"ttl": -1},
        ]
        for kwargs in cases:
            with self.subTest(**kwargs), self.assertRaises(ValueError):
                DNSAnswer(name="a", length=4, data=bytes(4), **kwargs)

    def test_rejects_length_overflow(self):
        with self.assertRaisesRegex(ValueError, "16 bits"):
            DNSAnswer(
                name="a",
                length=_UINT16_OVERFLOW,
                data=bytes(_UINT16_OVERFLOW),
            )

    def test_rejects_length_mismatch(self):
        for length in (3, 5):
            with (
                self.subTest(length=length),
                self.assertRaisesRegex(ValueError, "does not match"),
            ):
                DNSAnswer(name="a", length=length, data=bytes([8, 8, 8, 8]))


if __name__ == "__main__":
    unittest.main()
