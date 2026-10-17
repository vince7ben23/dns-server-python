# DNS Server

[CodeCrafters "Build Your Own DNS server"](https://app.codecrafters.io/courses/dns-server/overview) 的實作. Server 在 `127.0.0.1:2053` 監聽 UDP, 解析收到的 DNS query 並回傳 DNS response. 指定 `--resolver` 時作為 forwarder, 把每個 question 轉送給上游 resolver 查詢.

## 專案結構

```
app/
├── main.py              解析 --resolver, 選擇 lookup; UDP server 迴圈: 收 bytes → handle_query → 回傳
├── message/             DNS 封包格式, request 與 response 共用
│   ├── header.py        DNSHeader: 12-byte header 與 flags 編碼
│   ├── question.py      DNSQuestion: question section
│   ├── answer.py        DNSAnswer: answer section (resource record)
│   ├── common.py        多個 section 共用的規格常數 (message 大小上限)
│   ├── domain_name.py   domain name 的 label 編碼與解碼 (解碼支援 compression pointer)
│   └── parser.py        bytes → message: 解析任一方向的 DNS message
├── server/              我們作為 DNS server 的行為
│   ├── handler.py       解析 request, 逐一 lookup 每個 question, 組出 response
│   └── response.py      決定 response header 並編碼成 bytes
├── client/              我們作為 DNS client 向上游 resolver 查詢
│   └── forward.py       ForwardingLookup: 每個 question 拆成單獨的 query 轉送
└── libs/
    └── logger.py        全域 logger
tests/                   結構與 app/ 對應: tests/<pkg>/test_<mod>.py ↔ app/<pkg>/<mod>.py
└── fixtures.py          多個測試共用的常數與 helper
docs/                    學習筆記
├── dns-message-format.md   DNS message 格式, request 與 response 的異同
└── socket-notes.md         TCP 與 UDP socket 的差異
```

### 分層

- **`message/`**: DNS query 與 response 是同一種 message 格式 (RFC 1035 §4.1), 方向只靠 header 的 QR 等欄位區分, 所以各 section 的 dataclass 與編碼, 以及 bytes → 物件的解析都放在這裡共用.
- **`server/`**: 我們作為 server 的行為: 依 request 決定要回什麼, 再編碼成 bytes. answer 由 `Lookup` 提供, server 不知道來源.
- **`client/`**: 我們作為 client 的行為: 組 query 送給上游 resolver, 解析 reply. 提供符合 `Lookup` 的 `ForwardingLookup`.

`server/` 與 `client/` 依 runtime 角色區分, 都只依賴 `message/`, 彼此不 import, 由 `main.py` 組合.

### 運作流程

`handler` 對每個 question 各呼叫一次 lookup, 再依序合併 answers; response 的 ID 一律照抄 client 的 request. 是否指定 `--resolver` 只決定 lookup 用哪個實作. 以下都以一個含 2 個 question 的 query 為例.

#### 有 `--resolver`: forwarding server

lookup 為 `ForwardingLookup`. 同一個 service 對 client 是 **DNS server**, 對上游 resolver 是 **DNS client**.

```
 client               server/handler        client/forward            upstream resolver
   ├─── DNS server role ────┤                      ├───── DNS client role ─────┤
   │                        │                      │                           │
   │ query                  │                      │                           │
   │ ID=1234, Q1 Q2         │                      │                           │
   │───────────────────────▶│ parse request        │                           │
   │                        │── lookup(Q1) ───────▶│── query ID=0, Q1 ────────▶│
   │                        │◀────────────── A1 ───│◀──────────── reply A1 ────│
   │                        │── lookup(Q2) ───────▶│── query ID=0, Q2 ────────▶│
   │                        │◀────────────── A2 ───│◀──────────── reply A2 ────│
   │                        │ build_response       │                           │
   │◀───────────────────────│                      │                           │
   │ response               │                      │                           │
   │ ID=1234, Q1 Q2 A1 A2   │                      │                           │
```

- 上游 resolver 只回應單一 question 的 query, 所以每個 question 拆成單獨的 query 轉送.
- 轉送用的 query ID (0) 與 client 的 ID (1234) 無關.

#### 沒有 `--resolver`

lookup 為 `fixed_lookup`, 只有 **DNS server** 角色, 不經過 `client/`, answer 固定為 8.8.8.8.

```
 client               server/handler        server/handler.fixed_lookup
   ├─── DNS server role ────┤
   │                        │                      │
   │ query                  │                      │
   │ ID=1234, Q1 Q2         │                      │
   │───────────────────────▶│ parse request        │
   │                        │── lookup(Q1) ───────▶│
   │                        │◀──── A1 (8.8.8.8) ───│
   │                        │── lookup(Q2) ───────▶│
   │                        │◀──── A2 (8.8.8.8) ───│
   │                        │ build_response       │
   │◀───────────────────────│                      │
   │ response               │                      │
   │ ID=1234, Q1 Q2 A1 A2   │                      │
```

## 開發

需要先安裝 [`uv`](https://docs.astral.sh/uv/).

```sh
./your_program.sh                                    # 啟動 server (answer 固定 8.8.8.8)
./your_program.sh --resolver 8.8.8.8:53              # 啟動 forwarder
dig @127.0.0.1 -p 2053 +noedns codecrafters.io       # 送一個 query 測試
uv run python -m unittest discover -s tests -t .     # 跑測試
uv run ruff check && uv run ruff format              # lint 與 format
codecrafters submit                                  # 提交到 CodeCrafters
```

pre-commit 會跑 ruff check, ruff format 與 unit tests (見 `.pre-commit-config.yaml`).
