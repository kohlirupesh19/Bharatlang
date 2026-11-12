import React from 'react';
import { Mic, MessageSquare, BookOpen, CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck, Sparkles, Database, Languages, Cpu, Radio } from 'lucide-react';
import { SystemHealth } from '../types';
import { getTranslation } from '../i18n/translations';

interface HomeScreenProps {
  onNavigate: (screen: string) => void;
  systemHealth: SystemHealth | null;
  onSelectSampleQuery: (query: string) => void;
  selectedLanguage: string;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({
  onNavigate,
  systemHealth,
  onSelectSampleQuery,
  selectedLanguage
}) => {
  const t = getTranslation(selectedLanguage);

  return (
    <div className="space-y-8 pb-12">
      {/* Hero Header Card */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 rounded-3xl p-6 sm:p-10 text-white shadow-2xl border border-indigo-500/20">
        {/* Subtle ambient lighting effect */}
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 -mb-10 w-80 h-80 bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-3xl z-10">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-indigo-900/60 border border-indigo-500/40 text-indigo-300 text-xs font-semibold mb-5 shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>{t.home.badge}</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-black tracking-tight mb-3 text-white">
            {t.home.title}
          </h1>

          <p className="text-base sm:text-xl text-indigo-200 font-semibold mb-3 leading-snug">
            {t.home.subtitle}
          </p>

          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed mb-8 max-w-2xl">
            {t.home.description}
          </p>

          <div className="flex flex-wrap gap-3.5">
            <button
              onClick={() => onNavigate('voice')}
              className="flex items-center space-x-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-600 text-white font-bold text-sm px-5 py-3 rounded-xl shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <Mic className="w-4 h-4" />
              <span>{t.home.btnVoice}</span>
            </button>
            <button
              onClick={() => onNavigate('chat')}
              className="flex items-center space-x-2.5 bg-slate-800/90 hover:bg-slate-750 text-white font-bold text-sm px-5 py-3 rounded-xl border border-slate-700/80 shadow-md transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <MessageSquare className="w-4 h-4" />
              <span>{t.home.btnChat}</span>
            </button>
            <button
              onClick={() => onNavigate('kb')}
              className="flex items-center space-x-2 bg-slate-900/70 hover:bg-slate-800 text-slate-300 font-semibold text-sm px-4 py-3 rounded-xl border border-slate-700/60 transition-all"
            >
              <BookOpen className="w-4 h-4 text-indigo-400" />
              <span>{t.home.btnKb}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Model & Hardware Architecture Status Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* ASR Status */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-all hover:border-indigo-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1.5">
                <Radio className="w-3.5 h-3.5 text-emerald-600" />
                <span>{t.home.statusAsrTitle}</span>
              </span>
              <span className="flex items-center space-x-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                <span>Active</span>
              </span>
            </div>
            <p className="text-base font-extrabold text-slate-900">
              {systemHealth?.services.asr_engine.active_engine ?? '—'}
            </p>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              {t.home.statusAsrDesc}
            </p>
          </div>
        </div>

        {/* Translation & Dialect */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-all hover:border-indigo-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1.5">
                <Languages className="w-3.5 h-3.5 text-amber-600" />
                <span>{t.home.statusDialectTitle}</span>
              </span>
              <span className="flex items-center space-x-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                <span>Active</span>
              </span>
            </div>
            <p className="text-base font-extrabold text-slate-900">Varhadi Normalizer</p>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              {t.home.statusDialectDesc}
            </p>
          </div>
        </div>

        {/* Local LLM */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-all hover:border-indigo-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1.5">
                <Cpu className="w-3.5 h-3.5 text-indigo-600" />
                <span>{t.home.statusLlmTitle}</span>
              </span>
              {systemHealth?.services.ollama_local_llm.is_running ? (
                <span className="flex items-center space-x-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                  <span>Online</span>
                </span>
              ) : (
                <span className="flex items-center space-x-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                  <AlertTriangle className="w-3 h-3 text-amber-500" />
                  <span>Starting</span>
                </span>
              )}
            </div>
            <p className="text-base font-extrabold text-slate-900">Ollama Qwen2.5 1.5B</p>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              {t.home.statusLlmDesc}
            </p>
          </div>
        </div>

        {/* RAG Knowledge Base */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-all hover:border-indigo-200 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center space-x-1.5">
                <Database className="w-3.5 h-3.5 text-purple-600" />
                <span>{t.home.statusRagTitle}</span>
              </span>
              <span className="flex items-center space-x-1 text-[11px] font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-full border border-purple-200">
                <Database className="w-3 h-3 text-purple-500" />
                <span>{systemHealth?.services.rag_knowledge_base.total_chunks || 3} Chunks</span>
              </span>
            </div>
            <p className="text-base font-extrabold text-slate-900">Multilingual E5 + FAISS</p>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              {t.home.statusRagDesc}
            </p>
          </div>
        </div>
      </div>

      {/* Primary Farmer Demonstration Scenarios */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-sm">
        <div className="flex items-center space-x-2.5 mb-2">
          <ShieldCheck className="w-6 h-6 text-indigo-600 shrink-0" />
          <h2 className="text-lg sm:text-xl font-bold text-slate-900">
            {t.home.demoTitle}
          </h2>
        </div>
        <p className="text-xs sm:text-sm text-slate-600 mb-6">
          {t.home.demoSubtitle}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {t.home.sampleQueries.map((sq, idx) => (
            <div
              key={idx}
              onClick={() => onSelectSampleQuery(sq.query)}
              className="p-5 rounded-2xl border border-slate-200/90 bg-slate-50/80 hover:bg-indigo-50/60 hover:border-indigo-300 transition-all cursor-pointer group flex flex-col justify-between shadow-xs hover:shadow-md"
            >
              <div>
                <span className="inline-block text-[11px] font-bold text-indigo-700 bg-indigo-100/70 px-2.5 py-0.5 rounded-full mb-3">
                  {sq.tag}
                </span>
                <p className="text-sm font-semibold text-slate-900 leading-snug mb-2 group-hover:text-indigo-950">
                  "{sq.query}"
                </p>
                <p className="text-xs text-slate-500 italic leading-relaxed">
                  {sq.meaning}
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-200/60 flex items-center justify-between text-xs font-bold text-indigo-600 group-hover:text-indigo-700">
                <span>{t.home.askButton}</span>
                <ArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1.5 transition-transform" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
