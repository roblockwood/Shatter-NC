# Telnet Command Coverage Analysis

Comparison of commands documented in section_5.5.9.3.json vs current implementation.

## Currently Supported Commands

### Backend Telnet Client (`backend/app/clients/telnet_client.py`)

**Data Reading (LOD commands):**
- ✅ `LOD` - Read data (generic, supports any data name)
  - `get_memory_data()` - LOD MEM
  - `get_tool_table_data()` - LOD TOLNI1
  - `get_position_data()` - LOD POSNI1
  - `get_atc_magazine_data()` - LOD ATCTL
  - `get_directory_listing()` - DRQALL (Request directory of all data)
  - `parse_directory_listing(directory_data, control_type=None)` - Parse DRQALL response
    - Supports both C00 (11-byte entries: 8-byte name + 3-byte size in blocks) and D00 (18-byte entries: 8-byte name + 10-byte size in bytes) formats
    - Auto-detects format if control_type not provided
    - Converts block-based sizes to bytes for consistency
  - `detect_control_type(verbose=False)` - Detect control type (C00 vs D00) from directory listing
    - Solves catch-22 by parsing in BOTH formats simultaneously
    - Checks for multiple file patterns:
      - C00 indicators: PRDC# files (e.g., PRDC1, PRDC89) and SYSC# files (e.g., SYSC89, SYSC94)
      - D00 indicators: PRDD# files (e.g., PRDD1, PRDD89) and SYSD# files (e.g., SYSD89, SYSD94)
    - Returns "C00" or "D00" with confidence levels (high: 2+ indicators, medium: 1 indicator)
    - Tested on real machine (192.168.86.89) - correctly detected as C00 with 8 indicators

**Program Information:**
- ✅ `REDPRGN` - Get currently executed program information
  - `get_current_program_info()` - Returns program number, main program number, block number
- ✅ `REDPRG` - Get program content by character count
  - `get_current_program_content(character_count)` - Returns program content starting from current block

**Read Individual Data (RED commands):**
- ✅ `REDFILE` - Acquire file control data (memory usage, registrations)
  - `get_file_control_data()` - Returns memory and registration info
- ✅ `REDDATE` - Acquire date and time
  - `get_date_time()` - Returns machine date/time (YYYYMMDDHHMMSS)
- ✅ `REDPLCD` - Acquire PLC signal data (single signal)
  - `get_plc_signal(signal_type, signal_number)` - Returns PLC signal value
- ✅ `REDPLCR` - Acquire PLC signal data (range)
  - `get_plc_signal_range(signal_type, signal_number, data_size)` - Returns list of PLC signal values
- ✅ `REDCDBN` - Acquire all current data bank names
  - `get_all_data_bank_names()` - Returns list of data bank names
- ✅ `REDCDSL` - Acquire specific current data bank names
  - `get_data_bank_name(data_bank_name)` - Returns specific data bank name
- ✅ `REDTOFS` - Acquire tool compensation
  - `get_tool_compensation(tool_number, compensation_type)` - Returns tool compensation value
- ✅ `REDTLLF` - Acquire tool life
  - `get_tool_life(tool_number, life_type)` - Returns tool life value
- ✅ `REDTOFM` - Acquire H/D modal values
  - `get_hd_modal()` - Returns H and D modal values
- ✅ `REDMCNM` - Acquire macro variable (single)
  - `get_macro_variable(macro_number)` - Returns macro variable value (500-999)
  - Note: Only supports macro variables 500-999. Macro #302 (units) is not accessible via this command.
- ✅ `REDMCNM` (range) - Acquire macro variables in range
  - `get_macro_variable_range(start_macro, data_size)` - Returns list of macro variable values

**Infrastructure:**
- ✅ Connection management (connect/disconnect)
- ✅ Command frame building with checksum
- ✅ Response parsing
- ✅ Status code interpretation
- ✅ Async/await support

### Reference Implementation (`brother_cnc_export/brother_cnc_client.py`)

**Data Reading:**
- ✅ `LOD` - Read data (MEM, TOLNI1, POSNI1, ATCTL, DIR, PANEL, IO, SYSC89, SYSC94-99, PRD1-3)
- ✅ `load_directory()` - LOD DIR
- ✅ `load_memory()` - LOD MEM
- ✅ `load_panel()` - LOD PANEL
- ✅ `load_io()` - LOD IO
- ✅ `load_data()` - Generic LOD with data name
- ✅ `load_system_data()` - LOD SYSC89, SYSC94-99
- ✅ `load_production_data()` - LOD PRD1-3
- ✅ `load_position_data()` - LOD POSNI1, POSSI1

**Tool Operations:**
- ✅ `read_tool_offset()` - REDTOFS
- ✅ `write_tool_offset()` - WRTTOFS
- ✅ `read_tool_life()` - REDTLLF
- ✅ `write_tool_life()` - WRTTLLF
- ✅ `clear_tool_life()` - CLRTLLF

**ATC Operations:**
- ✅ `read_atc_magazine()` - LOD ATCTL + parser
- ✅ `change_atc_tool()` - CHGMAGM/CHGMAGS/CHGMAGK/CHGMAGC/CHGMAGD
- ✅ `assign_tool_to_magazine()` - CHGMAGM wrapper
- ✅ `remove_tool_from_magazine()` - CHGMAGD wrapper
- ✅ `set_tool_type()` - CHGMAGK wrapper

**I/O Operations:**
- ✅ `send_command("IOCREF", signal_name)` - Read I/O signal
- ✅ `send_multipart_command("IOCMOD", signal_name, "ON/OFF")` - Write I/O signal

**Position Operations:**
- ✅ `preset_relative_position()` - WRTREL
- ✅ `read_relative_position()` - LOD POSSI wrapper

**Machine Data:**
- ✅ `read_machine_data()` - REDMCNM (macro variables)
- ✅ `write_machine_data()` - WRTMCNM (macro variables)

## Missing Commands (Not Yet Implemented)

### 1. Data Operation Group - Folder Operations

- ❌ `FLDPWD` - Request current folder path
- ❌ `FLDDRQ` - Request folder list
- ❌ `FLDCHG` - Move current folder
- ❌ `FLDMAKE` - Create folder
- ❌ `FLDDEL` - Delete folder

### 2. Data Operation Group - Directory Operations

- ✅ `DRQALL` - Request directory of all data (new format)
- ❌ `DRQALL` (old) - Request directory (old format, 3-byte size)
- ❌ `DRQSEL` - Request directory by designating data name
- ❌ `DRQPRAL` - Ask detailed directory of registered programs only
- ❌ `DRQPRSL` - Request detailed directory by specifying registered program

### 3. Data Operation Group - File Operations

- ❌ `SAV` - Save data (upload file)
- ❌ `SAVBIN` - Save data (binary upload)
- ❌ `LODBIN` - Read data (binary download)
- ❌ `LODREC` - Read specified records in data file
- ❌ `DEL` - Delete specified data file
- ❌ `DELPRAL` - Delete all programs

### 4. Read Individual Data Group

- ✅ `REDFILE` - Acquire file control data (memory usage, registrations)
- ✅ `REDPRGN` - Acquire information on currently executed program
- ✅ `REDPRG` - Acquire currently executed programs by character count
- ✅ `REDDATE` - Acquire date and time
- ✅ `REDPLCD` - Acquire PLC signal data (single signal)
- ✅ `REDPLCR` - Acquire PLC signal data (range)
- ✅ `REDCDBN` - Acquire all current data bank names
- ✅ `REDCDSL` - Acquire specific current data bank names
- ✅ `REDTOFS` - Acquire tool compensation
- ✅ `REDTLLF` - Acquire tool life
- ✅ `REDTOFM` - Acquire H/D modal values
- ✅ `REDMCNM` - Acquire macro variable (single, 500-999)
- ✅ `REDMCNM` (range) - Acquire macro variables in range (500-999)

### 5. Write Individual Data Group

- ❌ `WRTREL` - Preset offsets for relative coordinate positions (we have wrapper but not direct command)
- ❌ `WRTTGRP` - Set tools to tool groups
- ❌ `WRTDATE` - Set date and time
- ❌ `WRTOPTM` - Set operation time
- ❌ `WRTPLCD` - Set PLC signal data
- ❌ `CLRTGRP` - Delete tools from tool group

### 6. Operation Control Group

- ❌ `MEMSTRT` - Start program operation
- ❌ `MEMSTOP` - Stop program operation (FEED HOLD control)
- ❌ `MEMQTST` - Start program externally
- ❌ `CHGPROG` - Change program selection
- ❌ `CHGDBK` - Change current data bank
- ❌ `CHGMODE` - Change mode (MNL, MDI, MEM, EDIT)
- ❌ `CHGKEY` - Change key status (DRYR, SNGL, OPTS, BLKS, MACL)

### 7. Auto Notification Group

- ❌ `SNC` - Control auto notification function (STRT, STOP, STAT)
- ❌ `SND` - Auto notification (NC → Notification host)

### 8. Access Control

- ❌ `ETHLGIN` - End temporary Ethernet access (with user/password)
- ❌ `ETHLGOT` - End temporary Ethernet access

## Priority Commands for Backend Integration

Based on current backend usage patterns, these commands should be prioritized:

### High Priority (Currently Used via HTTP/FTP)

1. **Program Information:** ✅ COMPLETE
   - ✅ `REDPRGN` - Get currently executed program (replaces HTTP `/running_log` parsing)
   - ✅ `REDPRG` - Get program content by character count

2. **Directory Operations:** ✅ PARTIAL
   - ✅ `DRQALL` - List files (replaces FTP directory listing) - Basic implementation complete
   - ❌ `DRQSEL` - List specific file by name
   - ❌ `DRQPRAL` - List programs with metadata

3. **File Operations:**
   - `SAV` - Upload files (currently FTP upload)
   - `LODBIN` - Download binary files (if needed)

4. **System Information:**
   - `REDFILE` - Get memory/file control data
   - `REDDATE` - Get machine date/time

### Medium Priority (Useful Features)

5. **Folder Management:**
   - `FLDPWD` - Get current folder
   - `FLDCHG` - Change folder
   - `FLDDRQ` - List folders

6. **Program Control:**
   - `MEMSTRT` - Start program
   - `MEMSTOP` - Stop program
   - `CHGPROG` - Change program

7. **Additional Data:**
   - `REDPLCD` - Read PLC signals
   - `REDMCNM` (range) - Read macro variable ranges

### Low Priority (Advanced Features)

8. **Auto Notification:**
   - `SNC` - Control auto notification
   - `SND` - Receive auto notifications

9. **Advanced File Operations:**
   - `LODREC` - Read specific records
   - `DEL` - Delete files
   - `DELPRAL` - Delete all programs

## Implementation Status Summary

**Backend Telnet Client:**
- ✅ Basic LOD commands (MEM, TOLNI1, POSNI1, ATCTL)
- ❌ Missing: ~40+ commands from protocol spec

**Reference Implementation:**
- ✅ Tool operations (read/write offsets, life)
- ✅ ATC operations (read/write magazine)
- ✅ I/O operations (read/write signals)
- ✅ Basic LOD commands
- ❌ Missing: Folder operations, directory queries, file upload/download, program control, auto notification

## Next Steps

1. **Phase 1:** ✅ **COMPLETE**
   - ✅ `CNCTelnetClient` class created
   - ✅ Connection management (port 10000, async/await)
   - ✅ `LOD` command for reading data files (MEM, TOLNI1, POSNI1, ATCTL)
   - ✅ Basic command/response handling with checksum
   - ✅ `REDPRGN` - Get currently executed program info
   - ✅ `REDPRG` - Get program content by character count
   - ✅ `DRQALL` - Request directory listing with parser (11-byte format)

2. **Phase 2-3:** Machine model and units detection (not command-related)

3. **Phase 5:** Replace HTTP/FTP reads - Need to add:
   - ✅ `REDPRGN` - Program information ✅ DONE
   - ✅ `DRQALL` - Directory listing ✅ DONE
   - ❌ `DRQSEL` - Directory listing by specific file name
   - ❌ `REDFILE` - System information (memory usage, registrations)

4. **Phase 6:** Enable writes - Already have tool/ATC writes in reference, need to add:
   - ❌ `SAV` - File upload
   - ❌ `MEMSTRT`/`MEMSTOP` - Program control
   - ❌ `WRTPLCD` - PLC signal writes

