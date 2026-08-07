import {
  machineConfigById,
  machinesForApiRegistry,
} from './fixtures/fleet';
import {
  deploymentDetailById,
  deploymentDetailForOnumber,
  deploymentsForMachine,
  metadataForFile,
  programRecordById,
  programsForPath,
  viewContentForFile,
} from './fixtures/programs';
import {
  compressorLayoutResponse,
  compressorStatusHistory,
  cycleHistory,
  DEMO_FORBIDDEN,
  machineAlarms,
  machineLayoutResponse,
  machinesSummary,
  panelDataForMachine,
  prd3StatusHistory,
  productionRunsTimeline,
  runningSummary,
  statusHistoryEvents,
} from './fixtures/history';

const loggedUnmatched = new Set<string>();

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function parseApiPath(url: string): { pathname: string; searchParams: URLSearchParams } | null {
  try {
    const parsed = new URL(url, 'http://demo.local');
    if (!parsed.pathname.includes('/api/')) return null;
    return { pathname: parsed.pathname, searchParams: parsed.searchParams };
  } catch {
    return null;
  }
}

function matchMachineId(pathname: string): number | null {
  const m = pathname.match(/^\/api\/machines\/(\d+)/);
  return m ? Number(m[1]) : null;
}

function matchCompressorId(pathname: string): number | null {
  const m = pathname.match(/^\/api\/compressors\/(\d+)/);
  return m ? Number(m[1]) : null;
}

export function routeDemoFetch(input: RequestInfo | URL, init?: RequestInit): Response | null {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
  const method = (init?.method ?? (typeof input !== 'string' && !(input instanceof URL) ? input.method : 'GET')).toUpperCase();
  const parsed = parseApiPath(url);
  if (!parsed) return null;

  const { pathname, searchParams } = parsed;

  if (method !== 'GET') {
    return jsonResponse(DEMO_FORBIDDEN, 403);
  }

  if (pathname === '/api/machines') {
    return jsonResponse(machinesForApiRegistry());
  }

  const machineId = matchMachineId(pathname);
  if (machineId !== null) {
    if (pathname === `/api/machines/${machineId}`) {
      const cfg = machineConfigById(machineId);
      return cfg ? jsonResponse(cfg) : jsonResponse({ detail: 'Not found' }, 404);
    }
    if (pathname === `/api/machines/${machineId}/programs`) {
      return jsonResponse(programsForPath(searchParams.get('path')));
    }
    if (pathname === `/api/machines/${machineId}/view`) {
      const filePath = searchParams.get('file_path') ?? '';
      const view = viewContentForFile(filePath);
      return jsonResponse({
        file_path: filePath,
        content: view.content,
        size: view.size,
        lines: view.lines,
      });
    }
    if (pathname === `/api/machines/${machineId}/metadata`) {
      return jsonResponse(metadataForFile(searchParams.get('file_path') ?? ''));
    }
    if (pathname === `/api/machines/${machineId}/layout`) {
      return jsonResponse(machineLayoutResponse());
    }
    if (pathname === `/api/machines/${machineId}/production-runs-timeline`) {
      return jsonResponse(productionRunsTimeline(machineId));
    }
    if (pathname === `/api/machines/${machineId}/status-history`) {
      return jsonResponse(statusHistoryEvents(machineId));
    }
    if (pathname === `/api/machines/${machineId}/prd3-status-history`) {
      const limit = Math.min(Number(searchParams.get('limit') ?? 500), 2000);
      const offset = Math.max(Number(searchParams.get('offset') ?? 0), 0);
      return jsonResponse(prd3StatusHistory(machineId, limit, offset));
    }
    if (pathname === `/api/machines/${machineId}/alarms`) {
      return jsonResponse(machineAlarms(machineId));
    }
    if (pathname === `/api/machines/${machineId}/cycle-history`) {
      return jsonResponse(cycleHistory(machineId));
    }
    if (pathname === `/api/machines/${machineId}/panel`) {
      return jsonResponse(panelDataForMachine(machineId));
    }
  }

  const compressorId = matchCompressorId(pathname);
  if (compressorId !== null) {
    if (pathname === `/api/compressors/${compressorId}/layout`) {
      return jsonResponse(compressorLayoutResponse());
    }
    if (pathname === `/api/compressors/${compressorId}/status-history`) {
      return jsonResponse(compressorStatusHistory());
    }
  }

  if (pathname === '/api/summary/running') {
    return jsonResponse(runningSummary());
  }
  if (pathname === '/api/summary/machines') {
    return jsonResponse(machinesSummary());
  }

  const deploymentsMatch = pathname.match(/^\/api\/programs\/machines\/(\d+)\/deployments$/);
  if (deploymentsMatch) {
    return jsonResponse(deploymentsForMachine(Number(deploymentsMatch[1])));
  }

  const deploymentByOnumberMatch = pathname.match(
    /^\/api\/programs\/machines\/(\d+)\/deployments\/by-onumber\/([^/]+)$/
  );
  if (deploymentByOnumberMatch) {
    return jsonResponse(deploymentDetailForOnumber(deploymentByOnumberMatch[2]));
  }

  const deploymentDetailMatch = pathname.match(/^\/api\/programs\/deployments\/(\d+)$/);
  if (deploymentDetailMatch) {
    return jsonResponse(deploymentDetailById(Number(deploymentDetailMatch[1])));
  }

  const programMatch = pathname.match(/^\/api\/programs\/(\d+)$/);
  if (programMatch) {
    return jsonResponse(programRecordById(Number(programMatch[1])));
  }

  if (pathname === '/api/settings/layout') {
    return jsonResponse(machineLayoutResponse());
  }

  if (import.meta.env.DEV && !loggedUnmatched.has(pathname)) {
    loggedUnmatched.add(pathname);
    console.debug('[demo] unmatched GET', pathname);
  }

  if (pathname.endsWith('/programs') || pathname.includes('history') || pathname.includes('timeline')) {
    return jsonResponse([]);
  }

  return jsonResponse({});
}

export async function demoFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
  nativeFetch: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<Response> {
  const routed = routeDemoFetch(input, init);
  if (routed) {
    await new Promise((r) => setTimeout(r, 40));
    return routed;
  }
  return nativeFetch(input, init);
}
