# Brother CNC-D00 Telnet / Ethernet Communication Reference

> Extracted from: **CNC-D00 Data Bank & Alarm Manual** (§1.7) and **CNC-D00 Operation Manual II** (§3.5–3.6)

---

## Table of Contents

1. [Ethernet Setup Overview](#1-ethernet-setup-overview)
2. [Communication Parameters — Ethernet/FTP (§1.7.4)](#2-communication-parameters--ethernetftp-§174)
3. [Communication Parameters — Common (§1.7.2)](#3-communication-parameters--common-§172)
4. [Communication Parameters — Security (§1.7.7)](#4-communication-parameters--security-§177)
5. [Protocol Type 2 — Control Format (§3.5.9.1)](#5-protocol-type-2--control-format-§3591)
6. [Completion Codes (§3.5.9.2)](#6-completion-codes-§3592)
7. [Access Control Commands (§3.5.9.3)](#7-access-control-commands-§3593)
8. [Data Operation Commands (§3.5.9.4)](#8-data-operation-commands-§3594)
9. [Individual Data Read Commands (§3.5.9.4 — CRED*)](#9-individual-data-read-commands-§3594--cred)
10. [Individual Data Write Commands (§3.5.9.4 — CWRT*)](#10-individual-data-write-commands-§3594--cwrt)
11. [Operation Control Commands (§3.5.9.5)](#11-operation-control-commands-§3595)
12. [Auto Notification Commands (§3.5.9.6)](#12-auto-notification-commands-§3596)
13. [Data Name Reference (§3.6.1)](#13-data-name-reference-§361)
14. [FTP Communication (§3.5.4.2)](#14-ftp-communication-§3542)

---

## 1. Ethernet Setup Overview

The NC unit acts as a **TCP/IP server (slave station)**. The client software (NC communication software) connects, issues command-response pairs using **Protocol Type 2**, then disconnects (or the server times out).

**Required network parameters to set on the NC:**

| Parameter No. | Item | Notes |
|---|---|---|
| 0201 | Host name | Up to 31 chars |
| 0202 | Use DHCP | 0: No, 1: Yes |
| 0203 | IP address | 12-digit string, no dots — e.g. `010172083001` = 10.172.83.1 |
| 0204 | Mask bit | 0–32 |
| 0205 | Default gateway | 12-digit string |
| 0206 | Auto acquire DNS | 0: No, 1: Yes |
| 0207 | DNS server address 1 | 12-digit string |
| 0208 | DNS server address 2 | 12-digit string |
| 0209 | Port No. | 1024–65535 — **TCP port the NC listens on for Protocol Type 2** |

> **NOTE:** `0.0.0.0`, `127.*.*.*`, and `255.*.*.*` cannot be set as IP addresses.

**Connection lifecycle:**
- The NC waits for a TCP connection at the port set in parameter 0209.
- Each command + response pair constitutes one logical session.
- If no command arrives within the time set in **Response monitoring time** (param 0221), the server closes the connection. Set to `0` to disable timeout (wait forever).
- Access restriction can be enabled via param 0216 (`Restrict Ethernet access = 1: Yes`). When restricted, a temporary-access command must be issued first (see §7).

---

## 2. Communication Parameters — Ethernet/FTP (§1.7.4)

| No. | Item name | Setting range | Description |
|---|---|---|---|
| 0201 | Host name | 31 one-byte chars | Hostname of this machine |
| 0202 | Use DHCP | 0: No / 1: Yes | Whether to use DHCP for IP assignment |
| 0203 | IP address | 12 digits (no dots) | e.g. `010172083001` = 10.172.83.1 |
| 0204 | Mask bit | 0–32 | Subnet mask in CIDR notation |
| 0205 | Default gateway | 12 digits | |
| 0206 | Auto acquisition of DNS | 0: No / 1: Yes | |
| 0207 | DNS server address 1 | 12 digits | |
| 0208 | DNS server address 2 | 12 digits | |
| 0209 | Port No. | 1024–65535 | **TCP port for Protocol Type 2 (slave station)** |
| 0210 | PLC port | 1024–65535 | TCP port for PLC communication |
| 0211 | FTP(S) server name/IP | 255 chars | FTP server when NC is client |
| 0212 | FTP(S) server port number | Default 21 (FTP) / 990 (FTPS) | |
| 0213 | User name as client | 255 chars | FTP login username |
| 0214 | Password as client | 255 chars | FTP login password |
| 0215 | FTP passive mode | 0: No / 1: Yes | |
| 0216 | Restrict Ethernet access | 0: No / 1: Yes | When Yes, all commands except temporary-access require authentication first |
| 0217 | Access timeout period | 0: No timeout / 1–99999 sec | How long temporary access remains active |
| 0218 | Server user name | 1–20 chars | Username for incoming connections when access is restricted |
| 0219 | Password as server | 8–20 chars | Password for incoming connections |
| 0220 | FTP time zone | ±hhmm | Time offset applied to FTP timestamps |
| 0221 | Response monitoring time | 0–999 sec | Server closes connection if no command received within this time. 0 = wait forever |
| 0222 | Checksum | 0: No / 1: Yes | Enables checksum in protocol footer |
| 0223 | Header/footer | 0: No / 1: Yes | Enables % header/footer in data transfer |
| 0224 | FTP response file size | 0: Old / 1: New | |
| 0225 | External output | 0: To master / 1: To slave | Where to send output data when NC is master |
| 0226 | HTTP | 0: Invalid / 1: Valid | Enable HTTP server |
| 0227 | HTTPS | 0: Invalid / 1: Valid | Enable HTTPS server |
| 0228 | FTP | 0: Invalid / 1: Valid | Enable FTP server |
| 0229 | FTPS | 0: Invalid / 1: Valid | Enable FTPS server |
| 0230 | OPC UA | 0: Invalid / 1: Valid | Enable OPC UA server |
| 0231 | Security communication for client | 0: No / 1: Yes | Use TLS when NC connects as FTP(S) client |
| 0235 | Extended comment input | 0: No / 1: Yes | Allow apostrophe-delimited comments over Ethernet |

---

## 3. Communication Parameters — Common (§1.7.2)

| No. | Item name | Setting range | Description |
|---|---|---|---|
| 0001 | Reset | 0: Invalid / 1: Valid | Execute reset when communication parameter is changed |
| 0002 | Data overwrite | 0: Prohibited / 1: Permitted | Allow overwriting programs received from external devices |
| 0003 | Remote operation | **0: Invalid / 1: Valid** | **Must be set to 1 to allow CMEM*, CCHG*, CIOC* operation commands** |
| 0004 | Slave station command alarm | 0: No alarm / 1: Alarm | Trigger alarm when slave commands are received |
| 0005 | Batch program input method | 0: Old method / 1: New method | |
| 0006 | File name comment | 0: Not output / 1: Output | Include comments when outputting program filenames |
| 0007 | Comment input extension | 0: Off / 1: On | Extended handling of apostrophe-delimited comments |
| 0008 | External output destination | 0: Master / 1: Slave | Where to send output when NC is master station |

---

## 4. Communication Parameters — Security (§1.7.7)

Used to configure the NC's TLS/HTTPS server certificate.

| No. | Item name | Setting range | Description |
|---|---|---|---|
| 0501 | Domain name | 237 chars | Domain name for the common name on the server certificate |
| 0502 | Valid period (days) | 365–7300 | Certificate validity period |
| 0503 | Public key and algorithm | 0: RSA(1024bit) / 1: RSA(2048bit) | |
| 0504 | Signature and algorithm | 0: SHA1 / 1: SHA256 / 2: SHA384 | |
| 0505 | Private-key password | 20 chars (half-width) | Minimum 8 chars; letters + numbers + symbols required |
| 0506 | Organization | 255 chars | For CSR |
| 0507 | Department | 255 chars | For CSR |
| 0508 | City | 255 chars | For CSR |
| 0509 | Prefecture/State | 255 chars | For CSR |
| 0510 | Country | 2 chars | e.g. `JP` |
| 0511 | Alternative domain name | 237 chars | Subject Alternative Name |
| 0512 | Scheduled notice days | 0–99 days | Days before cert expiry to trigger notice. 0 = no notice |
| 0513 | Connecting server cert warning level | 0: Operator message / 1: Alarm | What happens when connecting server cert has a problem |

---

## 5. Protocol Type 2 — Control Format (§3.5.9.1)

All commands over TCP use **NC communication device protocol type 2**. This is a text-based, Command-Response protocol.

### Basic structure

```
[Header 19 bytes] + [Data section (optional)] + [Footer 4 bytes]
```

### Header (19 bytes)

| Byte | Field | Description |
|---|---|---|
| 1 | `%` | Start symbol |
| 2 | `i1` | Identifier: `C` = Command, `R` = Response |
| 3–5 | `c1c2c3` | Command type — 3 bytes (see command tables below) |
| 6–9 | `f1f2f3f4` | Function — 4 bytes |
| 10–17 | `s1–s8` | Message — 8 bytes |
| 18–19 | `r1r2` | Completion code — 2 bytes (`00` = normal, other = error) |

> Blank boxes in command header tables represent spaces (0x20).

### Data section

The portion from immediately after the header `LF` to the `LF` before the footer.

### Footer (4 bytes)

```
LF ss %
```

- `ss` = 2-digit decimal **checksum**: sum of all character values from `%` in the header to the character before the footer `LF`, divided by 16 — take the remainder.
- `LF` = Line Feed (ISO), EOB (EIA), CR+LF (ASCII)
- `%` = tape start/end code

### Example flow

```
Client sends:   %C<cmd type><function><message>00\n<data>\nXX%
NC responds:    %R<cmd type><function><message><cc>\n<data>\nXX%
```

Where `cc` is the completion code (see §6) and `XX` is the checksum.

---

## 6. Completion Codes (§3.5.9.2)

Returned in bytes 18–19 of the response header.

| Code | Meaning |
|---|---|
| `00` | Normally ended |
| `01` | Invalid data received |
| `02` | Illegal slave command header |
| `04` | Illegal slave command checksum |
| `05` | In editing or operation mode — processing not possible |
| `06` | Editing error during file operation |
| `07` | Specified data/folder does not exist |
| `08` | Slave command data name incorrect / specified folder name abnormal |
| `09` | Specified data cannot be saved or deleted |
| `10` | Data protection enabled |
| `11` | Remote operation not permitted (check param 0003) |
| `13` | Item not within allowed range / record order not followed |
| `14` | Data version error |
| `15` | During special startup |
| `16` | Cannot read the specified data |
| `17` | Output of drawing data attempted during drawing |
| `18` | Folder already exists / folder exists when deleting |
| `19` | Designation of data size abnormal / binary data size abnormal |
| `20` | Binary data storage error |
| `23` | Access is restricted (need CETHGIN first) |
| `30` | Program does not exist / number out of range / not a data bank / data protection active |
| `31` | Attempt to change program in wrong mode / data bank changed with wrong parameter |
| `32` | Attempt to change selected program during operation or editing |
| `33` | Tool not registered in specified group |
| `34` | ATC: changing magazine item without assigned tool number |
| `35` | ATC: pot adjacent to specified pot contains a large tool |
| `36` | ATC tool change attempted during memory operation |
| `37` | ATC tool change attempted during MDI operation |
| `40` | Conflict — another port is using communication |
| `41` | Checksum error in specified data |
| `42` | Parity error in specified data |
| `43` | Specified data too large to store |
| `44` | Programs #8000–#8999 are write-protected |
| `45` | Machine unit system is different |
| `60` | Mode change not permitted |
| `67` | Operation not possible |
| `68` | No program |
| `69` | Not in memory operation mode |
| `70` | Outer door is open |
| `71` | Door is open |
| `72` | Side door is open |
| `74` | Servo control is on |
| `75` | [FEED HOLD] switch held down |
| `76` | Zero return not conducted |
| `86` | Memory operation mode active |
| `97` | Communicating |
| `98` | NC or conversation mode not selected correctly |

---

## 7. Access Control Commands (§3.5.9.3)

Required when `Restrict Ethernet access` (param 0216) is set to `1: Yes`.

### Temporary Ethernet Access — Login

**Command header:**

| `%` | `C` | `E` | `T` | `H` | `L` | `G` | `I` | `N` | (spaces) | `00` |
|---|---|---|---|---|---|---|---|---|---|---|

**Command data:**

```
Header  LF  Username  LF  Password  LF  Footer
```

- Username: 1–20 bytes — matches param 0218 (Server user name)
- Password: 8–20 bytes — matches param 0219 (Password as server)

If password is invalid, completion code `23` is returned.

### End Temporary Ethernet Access — Logout

**Command header:**

| `%` | `C` | `E` | `T` | `H` | `L` | `G` | `O` | `T` | (spaces) | `00` |
|---|---|---|---|---|---|---|---|---|---|---|

No command data required. Temporary access ends and the restriction is re-applied.

---

## 8. Data Operation Commands (§3.5.9.4)

> All folder operations act on the **current folder** of the connecting device. Move the current folder first using `CFLDCHG`, then issue data operations.

### Folder Operations

| Command | Header (c1c2c3 f1f2f3f4) | Data | Description |
|---|---|---|---|
| Get current folder path | `C F L D P W D ` | — | Returns path string (1–255 bytes) |
| Get folder list | `C F L D D R Q ` | — | Returns list of sub-folder names |
| Move current folder | `C F L D C H G ` | LF + folder name + LF | Folder name 1–255 bytes |
| Create folder | `C F L D M A K E` | LF + folder name + LF | Folder name 1–255 bytes |
| Delete folder | `C F L D D E L ` | LF + folder name + LF | Folder name 1–255 bytes |

**Folder navigation notes:**
- Root folder = `/`
- One level up = `..`
- `ABC` = move into `ABC` in current folder
- `/ABC` = move into `ABC` in root folder
- `../ABC` = move into `ABC` in parent folder

### Directory Request

| Command | Header | Description |
|---|---|---|
| All data (8-byte names, block size) | `C D R Q A L L ` | Data name = 8 bytes, Size = 3 bytes (blocks, 1 block = 128 bytes) |
| All data (long names, byte size) | `C D R Q A L L N` | Data name = 1–255 bytes, Size = 10 bytes |
| Registered programs only (8-byte names) | `C D R Q P R A L` | Returns: name, size, comment (60 bytes), date (14 bytes) |
| Registered programs (long names) | `C D R Q P R L A` | Returns: name, size, comment, date |
| Search by data name (8-byte) | `C D R Q` + n1–n8 | Specify data name in command header bytes s1–s8 |
| Search by data name (long) | `C D R Q S L L N` | Data name in command data |
| Specific registered program (8-byte) | `C D R Q P R S L` + n1–n8 | Returns: name, size, comment, date, attribute |
| Specific registered program (long) | `C D R Q P R L N` | Data name in command data; Returns: name, size, comment, date, attribute |

**Attribute values:** `0` = Normal, `1` = Program being used, `2` = Edit-prohibited

### Save Data (NC → Connecting Device)

| Command | Header | Description |
|---|---|---|
| Save to other party (8-byte name) | `C S A V` + n1–n8 | Data in command body |
| Save to connecting device (long name) | `C S A V L N` | Command data: LF + name + LF + data + LF |
| Save binary to other party (8-byte) | `C S A V B I N` + n1–n8 | Data body: LF + size (1–10 bytes) + LF + binary data |
| Save binary to connecting device | `C S A V B I L N` | Command data: LF + name + LF + size + LF + binary data |

### Read Data (Connecting Device → NC)

| Command | Header | Description |
|---|---|---|
| Read from other party (8-byte name) | `C L O D` + n1–n8 | Same response format as Save data |
| Read from connecting device (long) | `C L O D L N` | Command data: LF + name + LF |
| Read binary from other party (8-byte) | `C L O D B I N` + n1–n8 | Response: LF + size + LF + binary data |
| Read binary from connecting device | `C L O D B I L N` | Command data: LF + name + LF |
| Read specific records | `C L O D R E C` + n1–n8 | Command data: LF + Symbol1 + LF + ... + LF |

**Files supporting record read:** Workpiece coordinate zero (Type 1/2), Tool data (Type 1/2), Macro variables (Type 1/2).

### Delete Data

| Command | Header | Description |
|---|---|---|
| Delete from other party (8-byte) | `C D E L` + n1–n8 | — |
| Delete from connecting device (long) | `C D E L L N` | Command data: LF + name + LF |
| Delete all programs of other party | `C D E L P R A L` | Deletes all NC programs, machining data, and schedule programs in all folders |

---

## 9. Individual Data Read Commands (§3.5.9.4 — CRED*)

> Requires `Remote operation` (param 0003) = `1: Valid` for PLC signal commands.

| Command | Header | Description | Response data |
|---|---|---|---|
| File control data | `C R E D F I L E` | Program registration info | LF + registrations(4) + possible(4) + memory_used(10) + remaining(10) + LF |
| Current program number | `C R E D P R G N` | Program selected in memory op | LF + current_prog(4) + main_prog(4) + block_num(14) + LF |
| Executing program info | `C R E D P R G L` | 1–255 byte program names | LF + current_prog + LF + main_prog + LF + block_num(14) + LF |
| Program content | `C R E D P R G` + c1–c8 | c1–c8 = character count | LF + program_text + LF |
| Date and time | `C R E D D A T E` | — | LF + date(14 bytes: YYYYMMDDHHmmss) + LF |
| PLC signal (single) | `C R E D P L C D` + k1k2k3k4 + n1n2n3n4 | Signal type + number | LF + value + LF |
| PLC signal (range) | `C R E D P L C R` + k1k2k3k4 + n1n2n3n4 | + command data: LF + size(4) + LF | LF + size + values... + LF |
| All data bank names | `C R E D C D B N` | — | LF + names(8 bytes each)... + LF |
| Specific data bank names | `C R E D C D S L` + n1–n8 | Specify name (no data number suffix) | LF + name(8) + LF |
| Tool compensation (NC, T01–99) | `C R E D T O F S` + n1n2 + k1 | n1n2 = tool No., k1 = type | LF + compensation + LF |
| Tool compensation (NC, extended) | `C R E D T O F T` + n1n2n3 + k1 | T001–099 and T201–299 | LF + compensation + LF |
| Tool life (T01–99) | `C R E D T L L F` + n1n2 + k1 | k1: 0=unit,1=initial,2=warning,3=life | LF + value + LF |
| Tool life data (extended) | `C R E D T L L E` + n1n2n3 + k1 | T001–099 and T201–299 | LF + value + LF |
| H/D modal | `C R E D T O F M` | Current H/D modal | LF + H_modal(3) + LF + D_modal(3) + LF |
| Macro variable | `C R E D M C N M` + n1n2n3 | n1n2n3 = No. 500–999 | LF + value(12 bytes) + LF |
| Macro variables (range) | `C R E D M C N R` + n1n2n3 | + command data: LF + count(3) + LF | LF + count + values(12 each)... + LF |

**PLC signal types (k1k2k3k4):**

| Type | Description | Range |
|---|---|---|
| `X` | External input | 000–7FF (hex) |
| `Y` | External output | 000–7FF (hex) |
| `BX` | Internal input (bit) | 000–7FF (hex) |
| `BY` | Internal output (bit) | 000–7FF (hex) |
| `BDX` | Internal input (word) | 0–1023 |
| `BDXL` | Internal input (long word) | 0–1022 (even) |
| `BDY` | Internal output (word) | 0–1023 |
| `BDYL` | Internal output (long word) | 0–1022 (even) |
| `M` | Internal relay | 0000–9999 |
| `D` | Data register (word) | 0–8191 |
| `DL` | Data register (long word) | 0–8190 (even) |
| `LM0`–`LM4` | Local relay | 0000–4095 |
| `LD0`–`LD4` | Local data register | 0–8191 |

---

## 10. Individual Data Write Commands (§3.5.9.4 — CWRT*)

| Command | Header | Command data | Description |
|---|---|---|---|
| Preset relative coord offset | `C W R T R E L` + a1a2 | LF + offset1(10) [+ offset2...] + LF | a1a2 = axis 1–15; -1 = all axes |
| Set tool offset (T01–99) | `C W R T T O F S` + n1n2 + k1 | LF + offset + LF | 9 bytes for k1=0,2,4,6; 8 bytes for k1=1,3,5,7 |
| Set tool compensation (extended) | `C W R T T O F T` + n1n2n3 + k1 | LF + compensation + LF | T001–099 and T201–299 |
| Set tool life (T01–99) | `C W R T T L L F` + n1n2 + k1 | LF + value + LF | |
| Set tool life data (extended) | `C W R T T L L F` + n1n2n3 + k1 | LF + value + LF | T001–099 and T201–299 |
| Set tools to tool groups | `C W R T T G R P` + n1n2 + i1i2 + t1t2t3 | — | Group 01–30, order 01–30, tool 01–99/201–299 |
| Set date and time | `C W R T D A T E` | LF + date(14: YYYYMMDDHHmmss) + LF | |
| Set operation time | `C W R T O P T M` | LF + time(8: HHHHmmss) + LF | |
| Set PLC signal | `C W R T P L C D` + k1k2k3k4 + n1n2n3n4 | LF + value + LF | Signal types: Y, M, D, DL, LM, LD, etc. |
| Set macro variable | `C W R T M C N M` + n1n2n3 | LF + value(12 bytes) + LF | No. 500–999 |

**Clear commands:**

| Command | Header | Description |
|---|---|---|
| Initialize tool life | `C C L R T L L F` + n1n2n3 | Tool No. 1–99 and 201–299 |
| Delete tools from tool group | `C C L R T G R P` + n1n2 + i1i2 | Group 01–30, order 01–30 |

---

## 11. Operation Control Commands (§3.5.9.5)

> **All commands in this section require `Remote operation` (param 0003) = `1: Valid`.**
> Program targets refer to programs in the **current folder** — move folder first if needed.

### Operation Commands

| Command | Header | Data | Description |
|---|---|---|---|
| Start program (by number) | `C M E M S T R T` + p1p2p3p4 | — | Program number may be omitted (uses current selection) |
| Start program (by filename) | `C M E M S T L N` | LF + data_name(1–255) + LF | Start by data name (cannot be omitted) |
| Stop program | `C M E M S T O P` + s1s2s3 | — | s1s2s3: `ON ` = FEED HOLD on, `OFF` = FEED HOLD off |
| Start externally (by number) | `C M E M Q T S T` + p1p2p3p4 | — | Releases pallet reservation; program number optional |
| Start with pallet (by filename) | `C M E M Q T L N` | LF + data_name(1–255) + LF | Cancels any existing pallet start reservation |

> **IMPORTANT:** Once a program is started, it cannot be re-started while running — completion code `0077` is returned.

### Change Commands

| Command | Header | Data | Description |
|---|---|---|---|
| Change selected program (by number) | `C C H G P R O G` + p1p2p3p4 | — | Only available in memory/edit mode; not during operation |
| Change selected program (by filename) | `C C H G P R L N` | LF + data_name(1–255) + LF | Not possible during operation |
| Change current data bank | `C C H G D B K` + n1–n8 | — | Only in edit mode; not during operation |
| Change mode | `C C H G M O D E` + m1m2m3m4 | — | `MNL ` = Manual, `MDI ` = MDI, `MEM ` = Memory, `EDIT` = Edit |
| Change key status | `C C H G` + k1k2k3k4 + s1s2s3 | — | Keys: `DRYR`=DRY, `SNGL`=SINGLE, `OPTS`=OP.STP, `BLKS`=B.SKIP, `MACL`=M.LCK; States: `ON `, `OFF` |
| Change ATC tool | `C C H G M A G` + k1 + m1m2 + t1t2t3 | — | k1: M=tool#, S=group(NC)/main(Conv), K=type, C=color, D=delete |

### Signal Operation Commands

| Command | Header | Data/Response | Description |
|---|---|---|---|
| External I/O signal | `C I O C` + c1c2c3c4 + s1–s6 | LF + `ON `/`OFF` + LF | c1c2c3c4: `REF ` = Reference, `MOD ` = Operate; s1–s6 = signal name |

**Common controllable external input signals:**
`PRO1`, `PRO2`, `PRO4`, `PRO8`, `PRO16`, `PRO32`, `PRO64`, `EXSTRT`, `OUTST`, `EXSTOP`, `EXORG`, `EXZORG`, `CTURN`, `MFIN`, `ALMRLS`, `SPLOCK`, `ATCLCK`, `XYLOCK`, `ZLOCK`, `4LOCK`–`8LOCK`, `MDLOCK`, `KYLOCK`, `PRLOCK`, `EDLOCK`, `TLEDOK`, `UPEDOK`, `MPEDOK`, `WCEDOK`, `MGEDOK`, plus many others (see manual §1.6.4).

**Readable external output signals (reference only):**
`M00`, `M30/1`, `M08`, `M11`, `M12`, `STL` (cycle start lamp), `MEMOK`, `MEMMOD`, `EXPRUN`, `NCOK`, `ALM`, `ALM2`, `AUTO`, `SINGL`, `DRYRUN`, `RESTAT`, `TOOL`, plus many others (see manual §1.6.5).

---

## 12. Auto Notification Commands (§3.5.9.6)

The auto notification function pushes data from the NC to a configured host when triggered by the PLC's `SND_REQ` signal. Requires param 0401 (`Auto notification function`) = `1: Enable`.

### Control command (from external software to NC)

**Header:** `C S N C` + k1k2k3k4

- k1k2k3k4 options:
  - `STRT`: Start (only from configured notification host)
  - `STOP`: Stop
  - `STAT`: Acquire status

**Response data:** LF + return_value(6: -32768 to 32767) + LF

| Return value | Meaning |
|---|---|
| 0 | End normally (STRT/STOP) |
| 1 | Stopped (STAT/STOP) |
| 2 | Operating for host that issued command (STAT/STRT) |
| 3 | Operating for another host |
| 4 | Send being set by another host |
| 5 | Disabled — auto notification function disabled |
| 6 | Cannot start — invalid parameter |
| 7 | Cannot stop — notification currently being sent |

### Notification packet (NC → Notification Host)

**Command header:** `C S N D` (no additional fields)

**When `Type of sending data` = `0: No data`:**

```
header  LF  LF  Footer
```

**When data is included:**

```
header  LF  type_of_data(8)  leading_address(4)  data_length(4)  Data...Data  LF  Footer
```

| Data type | Description | Address range |
|---|---|---|
| `PLCDM   ` | PLC internal relay | 0–9999 |
| `PLCDM001` | PLC internal relay (extended) | 10000–10239 |
| `PLCDD   ` | PLC data register (word) | 0–8191 |
| `PLCDDL  ` | PLC data register (long word) | 0–8190 (even) |

**Auto notification error codes** (stored in data register set in param 0409):

| Code | Meaning |
|---|---|
| 0–99 | Completion code from notification destination response |
| 100 | No response received from destination |
| 101 | Response received but was not a number |
| 1100 | Failed TCP/IP connection to notification destination |
| 2100 | Timed out waiting for response |
| 3xxx | Checksum error (low 3 digits = completion code) |
| 4100 | Response was not an auto notification response |

---

## 13. Data Name Reference (§3.6.1)

Data is organized in sub-folders by type. The root folder is `/`. NC program data is in `/_DAT`.

### Programs

| Data | Name format |
|---|---|
| NC program | `O` + pppp (4-digit number) or 32-char string (A–Z, 0–9, `-`, `+`, `_`) |
| Machining data (Conversation) | `Q` + u + pppp |
| Schedule program (Conversation) | `J` + pppp |
| Old machining data (NOTE 2) | `K` + u + pppp |

### NC Data Files (stored in `/_DAT`)

| Description | Data name format |
|---|---|
| G/M code macro | `GMMCN` |
| User parameter | `UPRD` + u + n |
| External I/O signal | `EXIOD` + n |
| Communication parameter | `CMPRD` + n |
| Field network parameter | `FNPRD` + n |
| Machine parameter | `MPRD` + n |
| Special setting | `MSPSD` + n |
| Load monitor | `TLOA` |
| ATC tool data | `ATCTL` |
| Workpiece coordinate zero Type 1 (NC) | `POSN` + u + n |
| Workpiece coordinate zero Type 2 (NC) | `POSS` + u + n |
| Tool data Type 1 (NC) | `TOLN` + u + n |
| Tool data Type 2 (NC) | `TOLS` + u + n |
| Macro variables Type 1 (NC) | `MCRN` + u + n |
| Macro variables Type 2 (NC) | `MCRS` + u + n |
| Tool list (Conversation) | `TOLC` + u + n |
| Tool pattern (Conversation) | `TPTNC` + n |
| Tapping drill diameter (Conversation) | `TPUC` + u + n |
| Cutting condition (Conversation) | `CNDC` + u + n |

**Key notation:**
- `pppp` = program number
- `u` = unit system: `M` (Metric), `I` (Inch), `D` (Current)
- `n` = data number (0–9 and D; when 0, it represents No.10; when D, it represents the current plane)

---

## 14. FTP Communication (§3.5.4.2)

When param 0228 (`FTP`) or 0229 (`FTPS`) is enabled, the NC acts as an FTP/FTPS server.

**Supported FTP commands:**

```
USER  PASS  QUIT  PWD   XPWD  CWD   XCWD  CDUP  XCUP
TYPE  PORT  PASV  LIST  NLST  SIZE  MDTM  RETR  STOR
ABOR  DELE  MKD   XMKD  RMD   XRMD  RNFR  RNTO  NOOP
AUTH  PBSZ  PROT
```

**Notes:**
- `RNFR` returns an error when the specified name is a file (not a folder).
- When data protection is enabled on the NC, a data send via FTP will produce a send error — though some clients may not surface this as an explicit error.
- Connect using credentials set in params 0218 (username) and 0219 (password).

---

*Source documents: CNC-D00 Data Bank & Alarm Manual (2022-04-14, eCOM4DATA1-2) and CNC-D00 Operation Manual II (2022-02-17, eCOM4OP2_3)*
