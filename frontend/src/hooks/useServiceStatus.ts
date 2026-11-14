import { useEffect, useState } from 'react';
import { apiClient } from '../services/api';
import type { ServiceStatus } from '../types';

const POLL_INTERVAL_MS = 60_000;

/**
 * Plain service state for citizens, from /api/health `services.llm.is_running`.
 * Polls once a minute while the tab is visible; a failed request counts as unavailable.
 */
export function useServiceStatus(): ServiceStatus {
  const [status, setStatus] = useState<ServiceStatus>('checking');

  useEffect(() => {
    let cancelled = false;

    const check = async (): Promise<void> => {
      if (document.hidden) return;
      try {
        const health = await apiClient.getHealth();
        if (!cancelled) setStatus(health.services.llm.is_running ? 'available' : 'unavailable');
      } catch (err: unknown) {
        console.warn('Health check failed:', err);
        if (!cancelled) setStatus('unavailable');
      }
    };

    check();
    const timer = window.setInterval(check, POLL_INTERVAL_MS);
    document.addEventListener('visibilitychange', check);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', check);
    };
  }, []);

  return status;
}
