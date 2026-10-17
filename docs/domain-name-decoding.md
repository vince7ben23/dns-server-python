# Domain name 解析與 compression pointer

對應程式: `app/message/domain_name.py` 的 `decode_domain_name(data, offset)`.
格式總覽見 [dns-message-format.md](dns-message-format.md).

## 為何要用 compression pointer

**同一個 name 在一個封包裡會重複出現很多次.** response 至少帶回 question 的 name 一次, 每筆 answer 又各帶一次 name; 查到多個 IP 時, 每個 IP 是一筆 answer, name 就再重複一次.

以 `codecrafters.io` 為例, 編碼後是 17 bytes (`12 codecrafters 2 io 0`):

| | question | 3 筆 answer 的 name | name 總計 |
|---|---|---|---|
| 不壓縮 | 17 | 17 x 3 = 51 | 68 bytes |
| 用 pointer | 17 | 2 x 3 = 6 | 23 bytes |

這麼在意空間, 是因為傳統 DNS over UDP 的 message 上限是 **512 bytes** (RFC 1035 §2.3.4). 超過時 server 必須截斷並設 TC = 1, client 再改用 TCP 重查, 多一次來回. 壓縮能讓更多 record 擠進一個 UDP 封包.

pointer 不只能指向整個 name, 也能指向**共同的後綴**: `www.example.com` 和 `mail.example.com` 都能只寫自己的第一個 label, 再用 pointer 指向前面已經出現過的 `example.com`.

代價是解析變複雜: 不能一路往後讀, 要能跳回前面, 還要防範惡意的 pointer. 下面的規則都是為了處理這些問題.

## 一句話版本

從 `offset` 開始一個 byte 一個 byte 讀, 看每個 byte 的值決定它是什麼; 遇到 pointer 就跳到前面去讀, 但回傳的 offset 永遠是**原位置**上 name 的結尾, 讓呼叫端接著讀後面的欄位.

## 函式介面

- `data`: **整個 DNS message** (從 header 第 0 byte 開始). pointer 的 offset 是相對於封包開頭, 所以不能傳切片.
- `offset`: name 在 `data` 裡的起點.
- 回傳 `(name, next_offset)`: `next_offset` 是 name 後面下一個欄位 (例如 QTYPE) 的起點.

## `length = data[offset]` 讀到的是什麼

`bytes` 取單一索引得到 `int` (0..255), 不是 `bytes`:

```python
b"\x07example"[0]     # 7
b"\x07example"[0:1]   # b"\x07"
```

變數叫 `length`, 但讀進來時還不知道它代表什麼, 要看值:

| 值 | 高 2 bits | 意義 | 處理 |
|---|---|---|---|
| 0 | `00` | null byte, name 結束 | `break` |
| 1..63 | `00` | 一般 label 長度 | 讀後面 `length` 個 bytes |
| 64..191 | `01` / `10` | 規格保留 | `ValueError` |
| 192..255 | `11` | compression pointer 的第 1 個 byte | 算 target 後跳轉 |

一般 label 長度上限是 63 (`0b00111111`), 就是因為高 2 bits 要留給 pointer.

## Compression pointer 格式

```
      byte 0                 byte 1
+--+--+-----------------+-----------------+
| 1| 1| offset 高 6 bits | offset 低 8 bits |
+--+--+-----------------+-----------------+
       \_________ 14-bit offset _________/
```

```python
target = ((length & ~_POINTER_FLAG) << 8) | data[offset + 1]
```

`length & ~0b11000000` 清掉高 2 bits, 左移 8 位後與下一個 byte 組合. 例: `192, 12` -> `(0 << 8) | 12 = 12`.

## 三個容易忘的規則

1. **只允許往前指** (`target < offset`). 每次跳躍 offset 嚴格遞減, 而 offset 不會小於 0, 所以一定會結束. 少了這個檢查, 指向自己或 A -> B -> A 的 pointer 會讓解析無窮迴圈.
2. **只記錄第一個 pointer 的結尾** (`end_offset`). 原位置上的 name 只佔 "前面的 label + 第一個 pointer 的 2 bytes"; 跳過去之後讀到的 bytes 不屬於原位置, 連續跳多次也一樣.
3. **長度上限算展開後的長度** (`encoded_length`, 不含 pointer 本身). 擋掉靠 pointer 拼出超過 255 bytes 的 name.

## 例子

以下結果都實際跑過. 數字皆為 10 進位.

### 沒有 pointer

**例 1: 最基本**

```python
data = b"\x07example\x03com\x00"
decode_domain_name(data, 0)   # ('example.com', 13)
```

```
offset:  0   1..7      8   9..11  12
byte:    7   example   3   com    0
```

null byte 在 12, 回傳 13.

**例 2: root domain**

```python
decode_domain_name(b"\x00", 0)   # ('', 1)
```

**例 3: name 後面還有欄位**

```python
data = b"\x03www\x00" + b"\x00\x01\x00\x01"   # name + QTYPE=1 + QCLASS=1
decode_domain_name(data, 0)   # ('www', 5)
```

```
offset:  0   1..3   4   5  6    7  8
byte:    3   www    0   0  1    0  1
                        QTYPE   QCLASS
```

回傳的 5 是 QTYPE 的起點.

**例 4: offset 不是 0**

```python
data = b"\xaa\xbb\x03www\x00"
decode_domain_name(data, 2)   # ('www', 7)
```

### 有 pointer

以下共用開頭: offset 0..12 是 `example.com`.

```
offset:  0   1..7      8   9..11  12
byte:    7   example   3   com    0
```

**例 5: 整個 name 是 pointer**

```python
data = b"\x07example\x03com\x00" + b"\xc0\x00"
decode_domain_name(data, 13)   # ('example.com', 15)
```

```
offset:  13   14
byte:    192  0      -> pointer 指向 0
```

1. `data[13] = 192`, 是 pointer, target = 0
2. `end_offset = 15`, 跳到 0
3. 讀出 `example.com`
4. 回傳 15, 不是 13: 原位置只佔 13..14

**例 6: label + pointer**

```python
data = b"\x07example\x03com\x00" + b"\x03www\xc0\x00"
decode_domain_name(data, 13)   # ('www.example.com', 19)
```

```
offset:  13  14..16  17   18
byte:    3   www     192  0     -> pointer 指向 0
```

**例 7: pointer 指到的地方又有 pointer**

```python
data = (b"\x07example\x03com\x00"   # 0..12   example.com
        + b"\x03www\xc0\x00"         # 13..18  www + pointer -> 0
        + b"\x04mail\xc0\x0d")       # 19..25  mail + pointer -> 13
decode_domain_name(data, 19)   # ('mail.www.example.com', 26)
```

```
19: 讀出 mail
24: pointer -> 13   (第 1 次跳, end_offset = 26)
13: 讀出 www
17: pointer -> 0    (第 2 次跳, end_offset 已有值, 不更新)
 0: 讀出 example, com, 遇到 0 結束
```

### 錯誤情況

| data | offset | 錯誤 | 原因 |
|---|---|---|---|
| `b"\x07example\x03com"` | 0 | `missing its null terminator` | 讀到結尾還沒遇到 0 |
| `b"\xc0\x00"` | 0 | `must point backwards` | 指向自己, 否則會無窮迴圈 |
| `b"\x00\xc0\x05\x03www\x00"` | 1 | `must point backwards` | 在 1 指向 5, 往後指 |
| `b"\x45abc\x00"` | 0 | `unsupported label length byte 69` | 69 在保留範圍 64..191 |
| `b"\x03www\xc0"` | 0 | `compression pointer is truncated` | pointer 缺第 2 個 byte |
| `b"\x05ab\x00"` | 0 | `label content exceeds data length` | 宣告長度 5, 只剩 3 bytes |

## 實際會遇到的地方

上游 resolver 的 reply 中, answer name 通常是 `192 12`, 也就是指回 offset 12 的 question name. 見 [dns-message-format.md](dns-message-format.md) 的 Forwarding 一節.
