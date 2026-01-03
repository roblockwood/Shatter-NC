// Test script to verify getSeverityLevel logic
// Simulating what the frontend receives from the API

const testAlarms = [
  { code: 'IO0518', stop_level: '5', reset_level: '2', description: 'Air pressure low' },
  { code: 'IO2039', stop_level: '4', reset_level: '2', description: '*-axis not clamped' },
  { code: 'IO2047', stop_level: '4', reset_level: '2', description: '*-axis not clamped' },
  { code: 'SM7586', stop_level: '1', reset_level: '1', description: 'Carry out spindle run-in' },
  { code: 'CM7532', stop_level: '1', reset_level: '1', description: 'Ethernet communication error' },
];

// Simulate the getSeverityLevel function from AlarmPane.tsx
function getSeverityLevel(alarm) {
  // Use stop_level exclusively (higher number = more severe)
  // Stop levels: 5 = most critical, 4 = critical, 3 = error, 2 = warning, 1 = info
  if (alarm.stop_level) {
    const level = parseInt(alarm.stop_level, 10);
    if (!isNaN(level) && level >= 1 && level <= 5) {
      return level;
    }
  }
  
  // If stop_level is missing or invalid, default to 3 (error level)
  // This should rarely happen if the API is working correctly
  console.warn(`Alarm ${alarm.code} missing or invalid stop_level, defaulting to 3`);
  return 3;
}

console.log('Testing getSeverityLevel() with active alarms:');
console.log('='.repeat(60));

testAlarms.forEach(alarm => {
  const level = getSeverityLevel(alarm);
  console.log(`${alarm.code}:`);
  console.log(`  stop_level (raw): ${JSON.stringify(alarm.stop_level)} (type: ${typeof alarm.stop_level})`);
  console.log(`  parsed level: ${level}`);
  console.log(`  description: ${alarm.description}`);
  console.log();
});

console.log('Summary:');
const levels = testAlarms.map(a => ({ code: a.code, level: getSeverityLevel(a) }));
levels.forEach(({ code, level }) => {
  console.log(`  ${code}: level ${level}`);
});

