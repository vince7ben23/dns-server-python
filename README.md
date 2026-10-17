# DNS Server

[CodeCrafters "Build Your Own DNS server"](https://app.codecrafters.io/courses/dns-server/overview) 的實作. Server 在 `127.0.0.1:2053` 監聽 UDP, 解析收到的 DNS query 並回傳 DNS response.

## 專案結構

```
app/
├── main.py              UDP server 迴圈: 收 bytes → 解析 request → 組 response → 回傳
├── message/             DNS 封包格式, request 與 response 共用
│   ├── header.py        DNSHeader: 12-byte header 與 flags 編碼
│   ├── question.py      DNSQuestion: question section
│   ├── answer.py        DNSAnswer: answer section (resource record)
│   └── domain_name.py   domain name 的 label 編碼
├── request/
│   └── parser.py        bytes → message: 解析收到的 query
├── response/
│   └── builder.py       message → bytes: 決定回應內容並編碼
└── libs/
    └── logger.py        全域 logger
tests/                   結構與 app/ 對應: tests/<pkg>/test_<mod>.py ↔ app/<pkg>/<mod>.py
docs/                    學習筆記
├── dns-message-format.md   DNS message 格式, request 與 response 的異同
└── socket-notes.md         TCP 與 UDP socket 的差異
test_client.py           送任意 UDP payload 給 server 的小工具
```

### 分層

- **`message/`**: DNS query 與 response 是同一種 message 格式 (RFC 1035 §4.1), 方向只靠 header 的 QR 等欄位區分, 所以各 section 的 dataclass 與編碼放在這裡共用.
- **`request/`**: 處理收到的 bytes, 轉成 `message/` 的物件.
- **`response/`**: 依 request 決定要回什麼, 再編碼成 bytes.

## 開發

需要先安裝 [`uv`](https://docs.astral.sh/uv/).

```sh
./your_program.sh                                    # 啟動 server
dig @127.0.0.1 -p 2053 +noedns codecrafters.io       # 送一個 query 測試
uv run python -m unittest discover -s tests -t .     # 跑測試
uv run ruff check && uv run ruff format              # lint 與 format
codecrafters submit                                  # 提交到 CodeCrafters
```

pre-commit 會跑 ruff check, ruff format 與 unit tests (見 `.pre-commit-config.yaml`).
