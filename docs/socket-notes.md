# TCP（連線導向）與 UDP（訊息導向）

## 比較表

| | TCP | UDP |
|---|---|---|
| 連線 | 要先建立（三次握手） | 不需要 |
| 可靠性 | 保證送達、有順序 | 不保證 |
| 資料型態 | 位元組串流（沒有訊息邊界） | 獨立的資料包 |
| 收送 API | `send` / `recv` | `sendto` / `recvfrom` |
| 位址 | 僅需連線時取得一次 | 每個封包都要帶 |
| 伺服器模型 | 每個客戶端對到伺服器端個別的 **連線socket** | 所有客戶端都對到同一個伺服器端 socket |

## TCP：位址綁在連線上

```python
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("127.0.0.1", 8080))
s.listen()
conn, addr = s.accept()  # 三次握手完成，位址只在這裡拿一次
data = conn.recv(1024)  # 不會回傳位址
conn.send(b"reply")  # 不用指定位址
```

- `accept()` 會回傳一個**新的 socket**，專門負責和這一個客戶端通訊。
- 一條連線由 4-tuple 定義：`(本機 IP, 本機 port, 對方 IP, 對方 port)`。
- 需要查對方位址時，可以呼叫 `conn.getpeername()`。

### 伺服器端的兩種 socket

1. **監聽 socket（listening socket）**：只有一個，只負責接受新的連線，本身不傳送資料。
2. **連線 socket（connected socket）**：每次呼叫 `accept()` 就會建立一個，**每個客戶端各一個**。

```python
conn1, addr1 = s.accept()  # 客戶端 A
conn2, addr2 = s.accept()  # 客戶端 B
```

所有 socket 都用同一個本機 port，作業系統靠 4-tuple 區分封包要交給哪一個：

| socket | 本機 IP:port | 對方 IP:port |
|---|---|---|
| `s`（監聽） | 127.0.0.1:8080 | （無） |
| `conn1` | 127.0.0.1:8080 | 127.0.0.1:**51000** |
| `conn2` | 127.0.0.1:8080 | 127.0.0.1:**51001** |

客戶端的 port 是作業系統隨機分配的臨時 port，所以每條連線的 4-tuple 都不一樣。

**實際影響**：
- 要同時服務多個客戶端，就得同時處理多個 `conn`。常見做法有：每個連線開一個 thread、使用 `select` / `selectors`，或是使用 `asyncio`。
- 某個客戶端斷線時，只要 `conn.close()` 關閉那一個連線 socket，監聽 socket 和其他連線都不受影響。

## UDP：每個封包都是獨立的

```python
data, addr = sock.recvfrom(512)  # 每次都要知道是誰寄的
sock.sendto(b"reply", addr)  # 每次都要指定寄給誰
```

- 同一個 socket 可以收到很多不同客戶端的封包。
- 作業系統不會保留對話狀態，所以每個封包都要自己帶位址。
- 從頭到尾只有**一個 socket**，所有客戶端的封包都進到同一個地方，再靠 `recvfrom` 回傳的位址分辨是誰寄的（DNS 伺服器就是這種模型）。

### 補充：UDP 也可以呼叫 `connect()`

```python
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.connect(("8.8.8.8", 53))  # 不會握手，也不會建立真正的連線
sock.send(b"...")
data = sock.recv(512)
```

- 作用只是**記住預設的目的地**，並且只接收那個位址寄來的封包。
- 不會讓 UDP 變得可靠。
- 比較常用在客戶端；伺服器端通常還是用 `recvfrom` / `sendto`。
