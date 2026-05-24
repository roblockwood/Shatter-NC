# Heidenhain TNC OPC UA Monitoring

Shatter supports **Heidenhain TNC** controls (TNC 640 / 620 / TNC7 with OPC UA NC Server) for **monitoring only** via OPC UA.

## Requirements

- HEIDENHAIN OPC UA NC Server enabled (SIK options 56–61)
- NC software meeting Heidenhain Core Information Model support (see [official spec PDF](https://product.heidenhain.de/JPBC/image/FILEBASE_PUBLIC/1309365_07_A_01_1.pdf))
- OPC UA user with read access (username/password for v1)
- Network access to the control on port **4840** (default)

## Programming station setup (development)

1. Install the HEIDENHAIN programming station (VirtualBox demo) or use a network-connected TNC with OPC UA enabled.
2. On the control: enable OPC UA NC Server and create an OPC UA user (Setup manual §12.9).
3. Verify connectivity with **UaExpert** before adding the machine in Shatter:
   - Connect to `opc.tcp://<ip>:4840`
   - Browse `Objects → Machine`
   - Confirm `State`, `Channels`, and `Errors` nodes exist
4. In Shatter: **Add machine → Controller: Heidenhain TNC (OPC UA)**
   - IP address, OPC UA port (4840), username, password, channel (default `0`)

## Data collected (v1)

| Shatter field | OPC UA source |
|---------------|---------------|
| Online/offline | Poll success + `Machine.State` |
| `status` | `Machine.Channels.{n}.Program.ExecutionState` mapped to Brother-compatible strings |
| `program_name` | `Machine.Channels.{n}.Program.Name` |
| `alarms` | `Machine.Errors.AllActiveErrors` children |

## Status mapping

| Heidenhain program state | Shatter `status` |
|--------------------------|------------------|
| Running | operating |
| Idle, NotSelected, Finished | standby |
| Stopped, Interrupted | stopped |
| Error | error |
| NC not available | off |

Implementation: [`backend/app/controllers/heidenhain/status_mapping.py`](../backend/app/controllers/heidenhain/status_mapping.py)

## Browse paths used

Resolved at runtime via BrowseName walk (no hardcoded NodeIds):

- `Machine.State.CurrentState`
- `Machine.Channels.{channel}.Program.ExecutionState.CurrentState`
- `Machine.Channels.{channel}.Program.Name`
- `Machine.Errors.AllActiveErrors`

## Capabilities (UI)

Heidenhain v1 machines expose:

- `status`, `alarms`, `program`, `statusTimeline`

Hidden in the dashboard: tools, panel, file manager, upload, production runs, counters.

## Connection test

`POST /api/machines/{id}/test` returns an `opcua` result block for Heidenhain machines (Brother machines still test telnet + FTP).

## Known limitations (v1)

- Username/password auth only (X.509 certificates deferred)
- No file browser / program upload (Phase 2 — OPC UA file system)
- No tool table, panel, or cycle time
- One persistent OPC UA session per machine (respects SIK client-slot licensing)
- LSV-2 not supported (legacy iTNC fallback deferred)

## Manual validation checklist

- [ ] Add Heidenhain machine with valid OPC UA credentials
- [ ] Connection test returns `opcua.success: true`
- [ ] Dashboard shows online status within 2 poll intervals
- [ ] Program name updates when a program is selected on the control
- [ ] Status transitions appear in status timeline (operating ↔ standby)
- [ ] Active alarms appear in alarm pane
- [ ] Brother machines on the same dashboard unchanged

## Troubleshooting

- **Connection refused on 4840**: OPC UA server not enabled or firewall blocking
- **BadUserAccessDenied**: Wrong username/password or insufficient control user rights
- **Machine node not found**: Wrong NC software version or OPC UA option not licensed
- **Status stuck at off**: `Machine.State` not `NCIsAvailable` — control still booting or NC software not running

Contact HEIDENHAIN App Programming Helpline for information model questions; report Shatter-specific issues in the project repository.
