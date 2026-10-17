# DNS message 格式: request 與 response 共用

DNS 的 request (query) 和 response 是**同一種 message 格式** (RFC 1035 §4.1). 兩者的結構, 欄位和 bit 寬度完全相同, 差別只在欄位的值, 以及每個 section 實際放了什麼.

## 整體結構

```
+---------------------+
|        Header       |  固定 12 bytes
+---------------------+
|       Question      |  QDCOUNT 筆
+---------------------+
|        Answer       |  ANCOUNT 筆 resource record
+---------------------+
|      Authority      |  NSCOUNT 筆 resource record
+---------------------+
|      Additional     |  ARCOUNT 筆 resource record
+---------------------+
```

- 每個 section 有幾筆, 由 header 裡對應的 count 決定.
- count 為 0 的 section 在封包裡**不佔任何 bytes**, 所以封包裡沒有分隔符號, 只能照 count 依序往後讀.

| Section | Request | Response |
|---|---|---|
| Header | QR=0 | QR=1, 其餘見下方 header 欄位表 |
| Question | 要查的東西, 例如 `codecrafters.io` A IN | 通常把 request 的 question 原樣帶回 |
| Answer | 通常空的 | 查詢結果, 例如 `codecrafters.io` A `8.8.8.8` |
| Authority | 通常空的 | 負責該 domain 的 name server (NS record) |
| Additional | 通常空的; 有 EDNS 時會帶一筆 OPT record | 補充資料, 例如 NS 對應的 IP |

典型的 request 只有 Header + Question, response 則是 Header + Question + Answer.

## Header (12 bytes)

```
 0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                      ID                       |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|QR|   OPCODE  |AA|TC|RD|RA|   Z    |   RCODE   |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                    QDCOUNT                    |
|                    ANCOUNT                    |
|                    NSCOUNT                    |
|                    ARCOUNT                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
```

所有多 byte 欄位都是 big-endian (network byte order), 程式裡用 `struct` 的 `!` 前綴處理.

格式一樣, 但**誰填, 填什麼**不一樣:

| 欄位 | Request | Response |
|---|---|---|
| ID | client 隨機產生 | 照抄 request, client 靠它配對回應 |
| QR | 0 (query) | 1 (response) |
| OPCODE | client 指定查詢種類, 0 = standard query | 照抄 request |
| AA | 沒意義, 通常 0 | server 是否為該 domain 的權威來源 |
| TC | 通常 0 | 回應太大被截斷時設 1 |
| RD | client 希望遞迴查詢時設 1 | 照抄 request |
| RA | 沒意義, 通常 0 | server 是否支援遞迴 |
| Z | 0 | 0 |
| RCODE | 沒意義, 通常 0 | 查詢結果, 0 = no error, 4 = not implemented |
| QDCOUNT | 通常 1 | 通常照抄 (回應會帶回原本的 question) |
| AN/NS/ARCOUNT | 通常 0 | 依實際放了幾筆 record |

## 範例: 查詢 codecrafters.io 的 A record

### Request

```
04 d2  01 00  00 01  00 00  00 00  00 00     header
0c 63 6f 64 65 63 72 61 66 74 65 72 73       \x0c "codecrafters"
02 69 6f 00                                  \x02 "io" \x00 (name 結尾)
00 01  00 01                                 type = 1 (A), class = 1 (IN)
```

- `04 d2`: ID = 1234
- `01 00`: flags, 只有 RD = 1
- `00 01`: QDCOUNT = 1, 其他 count 都是 0, 所以 question 之後就結束了

### Response

```
04 d2  81 00  00 01  00 01  00 00  00 00     header
0c 63 6f ... 02 69 6f 00  00 01  00 01       question (原樣帶回)
0c 63 6f ... 02 69 6f 00                     answer: name
00 01  00 01                                 type = A, class = IN
00 00 00 3c                                  TTL = 60 秒
00 04                                        RDLENGTH = 4
08 08 08 08                                  RDATA = 8.8.8.8
```

- `04 d2`: ID 照抄 request
- `81 00`: QR = 1, RD 照抄 = 1
- `00 01 00 01`: QDCOUNT = 1, ANCOUNT = 1

## Domain name 壓縮

Response 裡同一個 name 常重複出現 (上例 question 和 answer 都是 `codecrafters.io`). 為了省空間, name 可以改用 2-byte 的 **compression pointer** 指回封包中前面出現過的位置:

- length byte 的最高 2 bits 為 `11` 就代表 pointer, 剩下 14 bits 是相對於封包開頭的 offset.
- 這也是一般 label 長度上限只有 63 (`0b00111111`) 的原因, 見 `app/message/domain_name.py`.
- 兩個方向都能用, 只是實際上多半出現在 response.

本專案目前的做法: 解析任何 message 時都支援 pointer (`decode_domain_name`), 組 response 時一律不壓縮 (`build_response`).

## Forwarding

指定 `--resolver` 時, server 不自己產生 answer, 而是轉送給上游 resolver:

- 上游 resolver 只回應單一 question 的 query, 所以 request 有多個 question 時拆成多個 query, 再把 answers 依序合併成一個 response.
- resolver reply 的 answer name 通常是指向它自己封包 offset 12 (question name) 的 pointer. 合併後的 response 裡, offset 12 永遠是第 1 個 question, 不能原樣複製 answer bytes; 所以先用 `parse_answer` 解開 name, 再由 `DNSAnswer.to_bytes()` 不壓縮重新編碼.
- response 的 ID 仍照抄 client 的 request, 轉送用的 query ID 與它無關.

## 對應到程式結構

因為格式共用, 編碼與解析都放在 `message/`; 上層則依 runtime 角色分開:

```
app/message/    各 section 的 dataclass, 編碼與解析 (兩個方向共用)
app/server/     作為 server: 決定回應內容 → bytes
app/client/     作為 client: 向上游 resolver 查詢
```

## 測試小提醒

用 `dig` 測試時加 `+noedns`, 否則 dig 會在 Additional section 多帶一筆 OPT record (EDNS), request 就不再只有 Header + Question.
