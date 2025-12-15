# Brother CNC Webserver API Endpoints

## Overview
- **IP Address**: 192.168.86.89
- **Server**: NC HTTPD (Custom HTTP server)
- **Model**: SX2
- **Content-Type**: text/html; charset=ISO-8859-1

## Available Communication Protocols

### 1. HTTP/Web Interface (Port 80)
Custom HTTP server with non-standard HTTP/1.1 implementation

### 2. FTP (Port 21)
- **URL**: ftp://192.168.86.89:21/
- **Purpose**: Data I/O (file transfer for G-code programs, etc.)

## Discovered HTTP Endpoints

### Main Navigation
- `/` or `/index` - Main homepage

### Monitor Display (`/monitor_menu`)
Parent menu for all monitoring functions

#### Workpiece Counter (`/work_counter`)
Displays 4 counters with:
- Count
- Current value
- Target value
- End signal value
- End/Signal status

#### Time Display (`/running_log`)
Machine operational data:
- Program name (current/previous)
- Cycle time
- Cutting time
- Non-cutting time
- Cutting time / cycle time percentage
- Operation end date and time
- Operation end counter
- Operation time
- Power on time: `01068:06:26` (1068 hours)
- Total operation time
- Current date/time

Alternative view: `/running_log?mode=1` - Operation time log

#### Measurement Results (`/measure_result`)
Stores measurement data with history:
- X, Y, Z coordinates
- Rotation
- Timestamp
- Historical data (Previous 1-8)

Pages available:
- `/measure_result?page=0` - Measurement result 1
- `/measure_result?page=1` - Measurement result 2
- `/measure_result?page=2` - Measurement result 3
- `/measure_result?page=3` - Measurement result 4

#### Status History (`/status_log`)
Logs of machine status changes with timestamps

#### Maintenance Notice (`/mainte_info`)
Maintenance alerts and scheduled maintenance information

#### Alarm Log (`/alarm_log`)
Historical alarm/error data

#### ATC Tool (`/tool`)
Automatic Tool Changer tool information and status

## Data Access Methods

### 1. HTTP GET Requests
All endpoints respond to simple HTTP/1.0 GET requests:
```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('192.168.86.89', 80))
sock.send(b'GET /endpoint HTTP/1.0\r\n\r\n')
response = sock.recv(8192)
```

### 2. FTP Access
For file transfers (G-code programs, etc.)
- URL: `ftp://192.168.86.89:21/`

### 3. Potential Additional Protocols
Based on manual documentation, may also support:
- FOCAS (if equipped)
- MTConnect (if configured)
- Custom TCP/UDP protocols

## FTP File System Structure

### Root Directory Files (/)
NC program files and system configuration:

**User Programs:**
- `O1001.NC` - `O5001.NC` - User G-code programs
- `PROGRAM/` - User program directory
- `SAMPLE/` - Sample program directory

**System Configuration Files:**
- `ATCTL.NC` - ATC (Automatic Tool Changer) control
- `HEACI.NC` - HEA control interface (664KB)
- `HTYPE1.LDR/CMT`, `HTYPE2.LDR/CMT` - Head type loaders/comments
- `STYPE1.LDR/CMT`, `STYPE2.LDR/CMT` - Spindle type loaders/comments
- `GCOMT.CMT` - G-code comments (51KB)

**System Monitor/Data Files (Live Data):**
- `ALARM.NC` - Current alarm status (622 bytes)
- `LOG.NC` - System log (881KB)
- `LOGBK.NC` - System log backup (7.9MB)
- `OPLOG.NC` - Operation log (224KB)
- `MONTR.NC` - Monitor data (440 bytes)
- `IO.NC` - I/O status (32KB)
- `MEM.NC` - Memory information (31 bytes)
- `PANEL.NC` - Panel data (61 bytes)
- `PDSP.NC` - Panel display (883 bytes)
- `VER.NC` - Version information (296 bytes)

**Counters and Maintenance:**
- `WKCNTR.NC` - Workpiece counter data (240 bytes)
- `MAINTC.NC` - Maintenance counter (2200 bytes)
- `MSRRSC.NC` - Measurement results (6847 bytes)
- `PAINT.NC` - Paint/interface settings (216 bytes)

**System Programs:**
- `SYSC89.NC` - `SYSC99.NC` - System control programs
- `PRD1.NC`, `PRDC2.NC`, `PRD3.NC` - Production programs
- `PLCDAT.NC`, `PLCMON.NC` - PLC data and monitoring
- `WVPRM.NC` - Wave parameters (3188 bytes)
- `SHTCUT.NC` - Shortcuts (110 bytes)

**Macro Programs:**
- `CMPR1.NC` - Comparison macro
- `CNDCI1.NC`, `CNDCM1.NC` - Condition check macros
- `EXIO1.NC` - External I/O macro (59KB)
- `MCRNI1.NC`, `MCRNM1.NC` - Macro programs
- `MPRC1.NC` - Macro process (112KB)
- `POSNI1.NC`, `POSNM1.NC` - Position macros
- `TOLNI1.NC`, `TOLNM1.NC` - Tool macros (35KB)
- `TOLCI1.NC`, `TOLCM1.NC` - Tool check macros
- `TLOAD1.NC` - Tool load
- `TPTNC1.NC`, `TPUCI1.NC`, `TPUCM1.NC` - Tool pattern/pickup macros
- `UPRCI1.NC`, `UPRCM1.NC` - Upper/update macros

### FTP Access Details
- **Authentication**: `anonymous` / `anonymous`
- **Permissions**: Most files read/write (rw-rw-rw-), some system files read-only
- **File Extensions**: `.NC` files (G-code/system files), `.LDR` (loaders), `.CMT` (comments)
- **Real-time Updates**: System monitor files (ALARM.NC, LOG.NC, MONTR.NC, etc.) update in real-time

## Key System Files for Real-Time Monitoring

Files that contain live machine data (updated every scan):
1. `ALARM.NC` - Current alarm/error status
2. `MONTR.NC` - Real-time monitor data
3. `WKCNTR.NC` - Live workpiece counter values
4. `IO.NC` - Current I/O states
5. `MEM.NC` - Memory status
6. `PANEL.NC` - Panel/operator interface state
7. `POSNI1.NC` - Position/coordinate system data (4489 bytes)

## Communication Protocol Summary

### Available Protocols:
1. **HTTP (Port 80)** - Web interface for monitoring and data display
2. **FTP (Port 21)** - File transfer and real-time data file access
3. **Potential**: FOCAS, MTConnect (check manual for configuration)

### Recommended Access Methods:

**For Real-Time Monitoring:**
- HTTP endpoints for formatted data display
- FTP download of `.NC` system files for raw data

**For Program Transfer:**
- FTP for uploading/downloading G-code programs

**For Control (if needed):**
- May require FOCAS library or direct serial/Ethernet protocol (see manual)

## Notes
- The HTTP server uses a non-standard HTTP/1.1 response format (missing version number)
- Standard curl commands fail; need to use raw socket connections
- All HTML responses use ISO-8859-1 encoding
- Webserver returns real-time machine data
- Current machine status shows: "Error occurred"
- Time data suggests machine has ~1068 hours of power-on time
- FTP requires credentials: `anonymous` / `anonymous`
- FTP connection may timeout; reconnect as needed
- System `.NC` files update in real-time and can be polled for current status

