import { useEffect, useState } from 'react';
import { FileText, ExternalLink, AlertTriangle, RefreshCw, History } from 'lucide-react';
import { apiClient } from '../services/api';
import { getTranslation } from '../i18n/translations';
import type { CorpusSource } from '../types';

interface DocumentsScreenProps {
  selectedLanguage: string;
}

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error' }
  | { kind: 'ready'; documents: CorpusSource[] };

/** Read-only list of the official documents answers come from, with links to the originals. */
export function DocumentsScreen({ selectedLanguage }: DocumentsScreenProps) {
  const t = getTranslation(selectedLanguage);
  const [state, setState] = useState<LoadState>({ kind: 'loading' });

  useEffect(() => {
    let cancelled = false;
    apiClient
      .getCorpusSources()
      .then((res) => {
        if (!cancelled) setState({ kind: 'ready', documents: res.documents });
      })
      .catch((err: unknown) => {
        console.warn('Loading the document list failed:', err);
        if (!cancelled) setState({ kind: 'error' });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      <div className="border-b border-slate-200 pb-5">
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">{t.docs.title}</h1>
        <p className="text-xs sm:text-sm text-slate-600 mt-1 max-w-3xl leading-relaxed">{t.docs.subtitle}</p>
      </div>

      {state.kind === 'loading' && (
        <div className="flex justify-center py-12 text-indigo-600">
          <RefreshCw className="w-6 h-6 animate-spin" />
        </div>
      )}

      {state.kind === 'error' && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-2xl text-sm flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
          <span>{t.docs.loadError}</span>
        </div>
      )}

      {state.kind === 'ready' && (
        <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm overflow-hidden">
          <div className="p-5 bg-slate-50 border-b border-slate-200 text-sm font-bold text-slate-800">
            {t.docs.countLabel}: {state.documents.length}
          </div>
          {state.documents.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">{t.docs.emptyList}</div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {state.documents.map((doc) => (
                <DocumentRow key={doc.doc_id} doc={doc} selectedLanguage={selectedLanguage} />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

interface DocumentRowProps {
  doc: CorpusSource;
  selectedLanguage: string;
}

function DocumentRow({ doc, selectedLanguage }: DocumentRowProps) {
  const t = getTranslation(selectedLanguage);
  const details = [
    doc.department,
    doc.gr_number ? `${t.docs.grNumber} ${doc.gr_number}` : null,
    doc.issue_date ? `${t.docs.issued} ${formatDate(doc.issue_date, selectedLanguage)}` : null
  ].filter((part): part is string => Boolean(part));

  return (
    <li className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div className="flex items-start space-x-3 min-w-0">
        <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600 shrink-0">
          <FileText className="w-5 h-5" />
        </div>
        <div className="min-w-0">
          <h2 className="text-sm font-bold text-slate-900 leading-snug break-words">{doc.title}</h2>
          {details.length > 0 && <p className="text-xs text-slate-500 mt-0.5 break-words">{details.join(' • ')}</p>}
          {doc.status === 'superseded' && (
            <span className="inline-flex items-center space-x-1 mt-1.5 text-[11px] font-semibold text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
              <History className="w-3 h-3" />
              <span>{t.docs.superseded}</span>
            </span>
          )}
        </div>
      </div>
      {doc.url && (
        <a
          href={doc.url}
          target="_blank"
          rel="noopener noreferrer"
          className="self-start sm:self-center shrink-0 inline-flex items-center space-x-1.5 px-3 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-indigo-700 hover:bg-indigo-50 transition-all"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          <span>{t.docs.openOfficial}</span>
        </a>
      )}
    </li>
  );
}

const DATE_LOCALES: Record<string, string> = { mr: 'mr-IN', 'mr-varhadi': 'mr-IN', hi: 'hi-IN', en: 'en-IN' };

function formatDate(isoDate: string, language: string): string {
  const parsed = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return isoDate;
  return parsed.toLocaleDateString(DATE_LOCALES[language] ?? 'mr-IN', { day: 'numeric', month: 'long', year: 'numeric' });
}
