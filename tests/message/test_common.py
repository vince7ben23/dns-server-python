import unittest

from app.message.common import MAX_MESSAGE_SIZE


class TestCommon(unittest.TestCase):
    def test_max_message_size_is_512_bytes(self):
        # 規格值, 刻意寫死 512
        self.assertEqual(MAX_MESSAGE_SIZE, 512)


if __name__ == "__main__":
    unittest.main()
