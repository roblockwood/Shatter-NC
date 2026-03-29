/**
 * SC2 json.json register IDs under block "3" for this Shatter deployment.
 * Stock Brown-Industries IDs differ by HMI/firmware; these match captured browser traffic.
 */
const SC2_OPERATIONAL_IDS = {
  POWER_STATE: 4049696,
  /** Primary compressor mode / status text for MQTT + Shatter infer_status */
  COMPRESSOR_STATE: 4472584,
  START_MODE: 4057536,
  PRESSURE: 3489792,
  OUTLET_TEMP: 3489952,
  LAST_POWER_DATE: 3200672,
  LAST_POWER_TIME: 3200752,
  /** HMI clock string (json.json block 3, SC2 “system status” frame) */
  PANEL_CLOCK: 3489872,
  KEY_LABEL: 4446952,
  KEY_TOGGLE: 4430360,
  KEY_CODE: 4419664,
  KEY_RIGHT: 4406224,
  RUN_HOURS_DISPLAY: 4361464,
  LOAD_HOURS_DISPLAY: 4348032,
  MAINTENANCE_HOURS_DISPLAY: 4301592,
} as const;

export class OperationalDto {
  powerState: string;
  compressorState: string;
  startMode: string;

  pressure: number;
  pressureUnit: string;

  inletTemp: number;
  inletTempUnit: string;

  outletTemp: number;
  outletTempUnit: string;

  motorTemp: number;
  motorTempUnit: string;

  lastPowerChange: Date;

  /** Raw HMI status text (preserves casing) for terminal-style panel */
  systemStatusDisplay: string;
  panelClock: string;
  keyLabel: string;
  keyToggle: string;
  keyCode: string;
  keyRight: string;
  runHoursDisplay: string;
  loadHoursDisplay: string;
  maintenanceHoursDisplay: string;

  constructor(data: any) {
    this.powerState = this.extractStringValue(data, SC2_OPERATIONAL_IDS.POWER_STATE)
      .trim()
      .toLowerCase();

    const statusDisplayRaw = this.extractStringValue(
      data,
      SC2_OPERATIONAL_IDS.COMPRESSOR_STATE,
    ).trim();
    this.systemStatusDisplay = statusDisplayRaw;

    const csRaw = statusDisplayRaw.toLowerCase();

    if (csRaw.includes('on load')) {
      this.compressorState = 'load';
    } else if (csRaw.includes('back pressure')) {
      this.compressorState = 'back pressure';
    } else {
      this.compressorState = csRaw;
    }

    const smRaw = this.extractStringValue(data, SC2_OPERATIONAL_IDS.START_MODE)
      .trim()
      .toLowerCase();
    if (smRaw === 'rc') {
      this.startMode = 'remote';
    } else {
      this.startMode = smRaw;
    }
    this.pressure = this.extractNumericValue(data, SC2_OPERATIONAL_IDS.PRESSURE);
    this.pressureUnit = this.extractUnit(data, SC2_OPERATIONAL_IDS.PRESSURE);

    // No mapped IDs yet for this SC2 build (single discharge temp only).
    this.inletTemp = 0;
    this.inletTempUnit = '';
    this.outletTemp = this.extractNumericValue(data, SC2_OPERATIONAL_IDS.OUTLET_TEMP);
    this.outletTempUnit = this.extractUnit(data, SC2_OPERATIONAL_IDS.OUTLET_TEMP);
    this.motorTemp = 0;
    this.motorTempUnit = '';

    const date = this.extractStringValue(data, SC2_OPERATIONAL_IDS.LAST_POWER_DATE);
    const time = this.extractStringValue(data, SC2_OPERATIONAL_IDS.LAST_POWER_TIME)
      .replace('AM', '')
      .replace('PM', '')
      .trim();
    this.lastPowerChange = new Date(`${date} ${time}`);

    this.panelClock = this.extractStringValue(data, SC2_OPERATIONAL_IDS.PANEL_CLOCK).trim();
    this.keyLabel = this.extractStringValue(data, SC2_OPERATIONAL_IDS.KEY_LABEL).trim();
    this.keyToggle = this.extractStringValue(data, SC2_OPERATIONAL_IDS.KEY_TOGGLE).trim();
    this.keyCode = this.extractStringValue(data, SC2_OPERATIONAL_IDS.KEY_CODE).trim();
    this.keyRight = this.extractStringValue(data, SC2_OPERATIONAL_IDS.KEY_RIGHT).trim();
    this.runHoursDisplay = this.extractStringValue(
      data,
      SC2_OPERATIONAL_IDS.RUN_HOURS_DISPLAY,
    ).trim();
    this.loadHoursDisplay = this.extractStringValue(
      data,
      SC2_OPERATIONAL_IDS.LOAD_HOURS_DISPLAY,
    ).trim();
    this.maintenanceHoursDisplay = this.extractStringValue(
      data,
      SC2_OPERATIONAL_IDS.MAINTENANCE_HOURS_DISPLAY,
    ).trim();
  }

  private static idMatches(itemId: unknown, wanted: number): boolean {
    if (itemId === wanted) return true;
    if (typeof itemId === 'string' && Number(itemId) === wanted) return true;
    return false;
  }

  /** SC2 json.json sometimes sends Value as number; stock code only read strings → zeros in UI. */
  private static coerceNumber(value: unknown): number | null {
    if (typeof value === 'number' && !Number.isNaN(value)) return value;
    if (typeof value === 'string') {
      const n = parseFloat(value.trim());
      return Number.isNaN(n) ? null : n;
    }
    return null;
  }

  private static coerceString(value: unknown): string {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value.trim();
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    return '';
  }

  private extractStringValue(data: any, id: number): string {
    const block = data?.['3'];
    if (!block || typeof block !== 'object') return '';
    for (const key in block) {
      if (!Object.prototype.hasOwnProperty.call(block, key)) continue;
      const item = block[key];
      if (!item || typeof item !== 'object') continue;
      if (!OperationalDto.idMatches(item['Id'], id)) continue;
      return OperationalDto.coerceString(item['Value']);
    }
    return '';
  }

  private extractNumericValue(data: any, id: number): number {
    const block = data?.['3'];
    if (!block || typeof block !== 'object') return 0;
    for (const key in block) {
      if (!Object.prototype.hasOwnProperty.call(block, key)) continue;
      const item = block[key];
      if (!item || typeof item !== 'object') continue;
      if (!OperationalDto.idMatches(item['Id'], id)) continue;
      const n = OperationalDto.coerceNumber(item['Value']);
      return n ?? 0;
    }
    return 0;
  }

  private extractUnit(data: any, id: number): string {
    const block = data?.['3'];
    if (!block || typeof block !== 'object') return '';
    for (const key in block) {
      if (!Object.prototype.hasOwnProperty.call(block, key)) continue;
      const item = block[key];
      if (!item || typeof item !== 'object') continue;
      if (!OperationalDto.idMatches(item['Id'], id)) continue;
      if (typeof item['Unit'] === 'string') return item['Unit'].trim();
    }
    return '';
  }

  toObj() {
    return {
      powerState: this.powerState,
      compressorState: this.compressorState,
      startMode: this.startMode,
      pressure: {
        value: this.pressure,
        unit: this.pressureUnit,
      },
      inletTemp: {
        value: this.inletTemp,
        unit: this.inletTempUnit,
      },
      outletTemp: {
        value: this.outletTemp,
        unit: this.outletTempUnit,
      },
      motorTemp: {
        value: this.motorTemp,
        unit: this.motorTempUnit,
      },
      lastPowerChange: this.lastPowerChange,
      sigmaPanel: {
        panelClock: this.panelClock,
        systemStatusDisplay: this.systemStatusDisplay,
        keyLabel: this.keyLabel,
        keyToggle: this.keyToggle,
        keyCode: this.keyCode,
        keyRight: this.keyRight,
        runHoursDisplay: this.runHoursDisplay,
        loadHoursDisplay: this.loadHoursDisplay,
        maintenanceHoursDisplay: this.maintenanceHoursDisplay,
      },
    };
  }
}
