# Dashboard Summary Feature

## Overview

The Dashboard Summary feature provides interactive, clickable machine status counts in the dashboard header that reveal detailed historical insights when clicked. This feature helps operators quickly understand machine utilization, connection health, and downtime patterns.

## User Guide

### Accessing Summaries

The dashboard header displays three clickable status counts:

```
MACHINES: 5  │  RUNNING: 3  │  ONLINE: 4  │  OFFLINE: 1  │  WS CONNECTED
                     ↑             ↑            ↑
                 [Clickable]   [Clickable]  [Clickable]
```

**To access a summary:**
1. Click on any of the three counts: RUNNING, ONLINE, or OFFLINE
2. A modal will appear with detailed information
3. Close the modal by:
   - Clicking the X button in the top-right corner
   - Clicking outside the modal
   - Pressing the Escape key

### Running Summary

**Access:** Click "RUNNING: X" in the dashboard header

**Purpose:** Analyze machine utilization over a selected time period

**Features:**
- Time range selector (1 Hour, 4 Hours, 24 Hours, 7 Days, 30 Days)
- Machines sorted by total run time (highest first)
- Visual percentage bar showing utilization
- Current running status and program

**Data Displayed:**
| Column | Description |
|--------|-------------|
| MACHINE | Machine name (colored by current status) |
| RUN TIME | Total time machine was running (formatted: "12h 30m") |
| PERCENTAGE | Percentage of time range spent running (with visual bar) |
| LAST ACTIVE | When the machine last ran or is currently running |
| PROGRAM | Current O-number program (if running) |

**Use Cases:**
- Identify underutilized machines
- Track production activity over different time periods
- Compare machine usage patterns
- Verify machines are running expected programs

### Online Summary

**Access:** Click "ONLINE: X" in the dashboard header

**Purpose:** Monitor connection health and service availability for online machines

**Features:**
- Machines sorted by online duration (longest first)
- Connection health indicators
- Service status for HTTP and FTP
- Last seen timestamps

**Data Displayed:**
| Column | Description |
|--------|-------------|
| MACHINE | Machine name (green for online) |
| ONLINE | Duration machine has been online (formatted: "4h 30m") |
| HEALTH | Connection health with indicator (● healthy, ◐ degraded, ○ stale) |
| SERVICES | HTTP and FTP service status with icons |
| LAST SEEN | How recently the machine was contacted |

**Connection Health Levels:**
- **Healthy** (●): Last seen < 30 seconds ago (normal polling)
- **Degraded** (◐): Last seen < 5 minutes ago (possible network issues)
- **Stale** (○): Last seen > 5 minutes ago (connection problems)

**Use Cases:**
- Verify all expected machines are connected
- Identify machines with intermittent connectivity
- Monitor network health across the fleet
- Diagnose service-specific issues (HTTP vs FTP)

### Offline Summary

**Access:** Click "OFFLINE: X" in the dashboard header

**Purpose:** Diagnose offline machines and identify service failures

**Features:**
- Machines sorted by offline duration (longest first)
- Specific service failure reasons
- Last known machine status
- Offline timestamps

**Data Displayed:**
| Column | Description |
|--------|-------------|
| MACHINE | Machine name (red for offline) |
| OFFLINE | Duration machine has been offline (formatted: "6h 15m") |
| OFFLINE SINCE | Exact timestamp when machine went offline |
| SERVICE ERRORS | Specific HTTP/FTP error messages |
| LAST STATUS | Last known operational status before offline |

**Use Cases:**
- Prioritize which machines need attention (by offline duration)
- Identify root cause (HTTP vs FTP, connection timeout vs refused)
- Track when machines went offline for maintenance logs
- Verify machines are intentionally offline vs unexpected failures

## Data Sources

The summary feature aggregates data from multiple TimescaleDB tables:

### Running Summary
- **Primary Table:** `production_runs` (TimescaleDB hypertable)
- **Fields Used:**
  - `started_at` - Run start time
  - `ended_at` - Run end time (NULL if still running)
  - `duration_seconds` - Total run duration
  - `program_name` - O-number of running program
- **Calculation:** Sums duration for all runs within selected time range
- **Real-time Status:** From WebSocket cached machine status

### Online Summary
- **Primary Tables:**
  - `machines` - Current machine configuration
  - `machine_status_events` - Historical status changes
- **Fields Used:**
  - `last_seen_at` - Last successful communication
  - `enabled` - Whether machine is active
  - Status event timestamps for online duration calculation
- **Connection Health:** Calculated from `last_seen_at` timestamp delta
- **Service Status:** From WebSocket polling service cache

### Offline Summary
- **Primary Tables:**
  - `machines` - Current machine configuration
  - `machine_status_events` - Historical status changes
- **Fields Used:**
  - `last_seen_at` - When machine was last reachable
  - Most recent status event for offline timestamp
  - Last known status from event history
- **Service Errors:** From WebSocket polling service error cache

## Technical Details

### Time Range Options (Running Summary)

| Value | Duration | Use Case |
|-------|----------|----------|
| 1h | 1 Hour | Current shift monitoring |
| 4h | 4 Hours | Half-day analysis |
| 24h | 24 Hours | Daily production review (default) |
| 7d | 7 Days | Weekly trends |
| 30d | 30 Days | Monthly utilization reports |

### API Endpoints

- `GET /api/summary/running?time_range=24h` - Running summary with configurable range
- `GET /api/summary/online` - Online machines with health data
- `GET /api/summary/offline` - Offline machines with diagnostics

See [API_QUICK_REFERENCE.md](../API_QUICK_REFERENCE.md) for detailed API documentation.

### Performance Characteristics

- **Query Optimization:** Leverages TimescaleDB's time-series optimizations
- **Response Time:** < 500ms for fleets up to 100 machines
- **Caching:** Real-time status from WebSocket manager cache
- **Data Retention:**
  - Production runs: 5 years
  - Status events: 1 year
  - Alarm events: 2 years

## Troubleshooting

### Summary Shows No Data

**Problem:** Modal displays "No data available" or "No machines" message

**Solutions:**
1. **For Running Summary:**
   - Verify machines have been running during selected time range
   - Try selecting a longer time range (e.g., 7d or 30d)
   - Check that production run logging is enabled
   - Verify machines are actually running programs (not just idle/online)

2. **For Online Summary:**
   - Confirm machines are physically powered on and connected to network
   - Check WebSocket connection status in dashboard header
   - Verify machines are enabled in configuration
   - Test network connectivity to machine IP addresses

3. **For Offline Summary:**
   - If no machines show as offline, this is expected behavior (good!)
   - Verify machines are configured with correct IP addresses
   - Check that polling service is running (`/health` endpoint)

### Incorrect Run Time Percentages

**Problem:** Run percentage seems wrong or > 100%

**Possible Causes:**
- Machine clock not synchronized (affects timestamp calculations)
- Production run ended_at timestamps missing (active runs counted incorrectly)
- Time range selector changed while viewing data

**Solutions:**
- Verify machine system time matches server time
- Close and reopen modal to fetch fresh data
- Check backend logs for database query errors

### Connection Health Always "Stale"

**Problem:** All online machines show degraded/stale health status

**Possible Causes:**
- Polling service not running or paused
- Network latency > 30 seconds
- Server system time incorrect

**Solutions:**
- Check `/health` endpoint to verify polling service status
- Review polling interval settings (default: 5 seconds)
- Verify server and machine network connectivity

### Service Errors Not Specific

**Problem:** Service errors show "Unknown" or generic messages

**Possible Causes:**
- Machine went offline before first polling attempt
- Firewall blocking specific ports
- Service-specific failures not cached

**Solutions:**
- Use `/api/machines/{id}/test` endpoint for detailed connection test
- Check machine firewall settings (ports 80, 21)
- Review backend logs for detailed error messages

## Best Practices

### For Operators

1. **Daily Routine:**
   - Check Running Summary (24h) at start of shift
   - Identify machines with low utilization
   - Verify all expected machines are online

2. **When Issues Arise:**
   - Start with Offline Summary to identify problems
   - Check service errors for diagnostic clues
   - Use Online Summary to verify connection health after fixes

3. **Weekly Reviews:**
   - Run Running Summary (7d) to identify trends
   - Compare machine utilization across the fleet
   - Plan maintenance for underutilized machines

### For Administrators

1. **Performance Monitoring:**
   - Monitor query response times via browser dev tools
   - Review TimescaleDB compression policies
   - Archive old production run data if database grows large

2. **Data Quality:**
   - Verify machine clocks are synchronized (NTP)
   - Check that polling service uptime is high
   - Validate production run start/end timestamps are accurate

3. **Network Health:**
   - Monitor connection health indicators across fleet
   - Investigate machines frequently showing degraded health
   - Review network infrastructure if many timeouts occur

## Future Enhancements

Potential improvements to this feature:

1. **Export Functionality:**
   - Download summary data as CSV/Excel
   - Generate PDF reports with charts

2. **Drill-Down Details:**
   - Click machine in summary to view detailed history
   - Show timeline of status changes
   - Link to specific production runs

3. **Alerts and Notifications:**
   - Alert when machine offline > threshold
   - Notify when utilization drops below target
   - Email daily summary reports

4. **Advanced Filtering:**
   - Filter by machine tags
   - Show only machines with alarms
   - Custom date range picker

5. **Visualizations:**
   - Run time charts and graphs
   - Availability heatmaps
   - Service uptime SLA tracking
