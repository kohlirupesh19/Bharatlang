import { CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react';
import type { ServiceStatus } from '../types';
import type { TranslationDictionary } from '../i18n/translations';

interface ServiceStatusBadgeProps {
  status: ServiceStatus;
  t: TranslationDictionary;
}

const STYLES: Record<ServiceStatus, string> = {
  checking: 'bg-slate-800/80 border-slate-700/80 text-slate-300',
  available: 'bg-emerald-900/40 border-emerald-700/60 text-emerald-200',
  unavailable: 'bg-amber-900/40 border-amber-700/60 text-amber-200',
};

/** "Service available / temporarily unavailable" in plain words, for the navbar. */
export function ServiceStatusBadge({ status, t }: ServiceStatusBadgeProps) {
  const Icon = status === 'available' ? CheckCircle2 : status === 'unavailable' ? AlertTriangle : Loader2;
  return (
    <div
      role="status"
      aria-live="polite"
      className={`hidden sm:flex items-center space-x-1.5 text-xs px-3 py-1.5 rounded-xl border ${STYLES[status]}`}
    >
      <Icon className={`w-3.5 h-3.5 ${status === 'checking' ? 'animate-spin' : ''}`} />
      <span className="font-medium">{t.status[status]}</span>
    </div>
  );
}
