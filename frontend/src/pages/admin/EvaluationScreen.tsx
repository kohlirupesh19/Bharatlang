import React, { useState, useEffect } from 'react';
import { BarChart3, Play, Activity, Award } from 'lucide-react';
import { apiClient } from '../../services/api';
import { getAdminTranslation } from '../../i18n/adminTranslations';

interface EvaluationScreenProps {
  selectedLanguage: string;
}

export const EvaluationScreen: React.FC<EvaluationScreenProps> = ({ selectedLanguage }) => {
  const t = getAdminTranslation(selectedLanguage);

  const [evalData, setEvalData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRunningAsr, setIsRunningAsr] = useState(false);
  const [isRunningRag, setIsRunningRag] = useState(false);
  const [activeModel, setActiveModel] = useState('');
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [asrResult, setAsrResult] = useState<any>(null);
  const [ragResult, setRagResult] = useState<any>(null);

  const fetchSummary = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getEvaluationSummary();
      setEvalData(data);
      if (data.recent_benchmarks && data.recent_benchmarks.length > 0) {
        setAsrResult(data.recent_benchmarks[0].details);
      }
      if (data.rag_retrieval_benchmark) {
        setRagResult(data.rag_retrieval_benchmark);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchModels = async () => {
    try {
      const data = await apiClient.getAsrModels();
      setAvailableModels(data.available_engines ?? []);
      setActiveModel(data.active_engine ?? '');
    } catch (e) {
      console.error('Failed to load ASR models', e);
    }
  };

  useEffect(() => {
    fetchSummary();
    fetchModels();
  }, []);

  const handleRunAsr = async () => {
    setIsRunningAsr(true);
    try {
      const res = await apiClient.runAsrBenchmark(activeModel);
      setAsrResult(res.results);
      await fetchSummary();
    } catch (e) {
      console.error(e);
    } finally {
      setIsRunningAsr(false);
    }
  };

  const handleRunRag = async () => {
    setIsRunningRag(true);
    try {
      const res = await apiClient.runRagBenchmark();
      setRagResult(res.results);
      await fetchSummary();
    } catch (e) {
      console.error(e);
    } finally {
      setIsRunningRag(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            {t.eval.title}
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-1">
            {t.eval.subtitle}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleRunAsr}
            disabled={isRunningAsr}
            className="flex items-center space-x-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-600/20 transition-all cursor-pointer"
          >
            <Play className={`w-3.5 h-3.5 ${isRunningAsr ? 'animate-spin' : ''}`} />
            <span>{isRunningAsr ? t.eval.runningAsr : t.eval.btnRunAsr}</span>
          </button>
          <button
            onClick={handleRunRag}
            disabled={isRunningRag}
            className="flex items-center space-x-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-md transition-all cursor-pointer"
          >
            <Activity className={`w-3.5 h-3.5 ${isRunningRag ? 'animate-spin' : ''}`} />
            <span>{isRunningRag ? t.eval.runningRag : t.eval.btnRunRag}</span>
          </button>
        </div>
      </div>

      {/* Section 1: ASR Evaluation Metrics */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Award className="w-5 h-5 text-indigo-600" />
            <span>{t.eval.asrSectionTitle}</span>
          </h2>
          <div className="flex items-center space-x-2">
            <label className="text-xs text-slate-500 font-bold">{t.eval.modelSelectLabel}</label>
            <select
              value={activeModel}
              onChange={(e) => setActiveModel(e.target.value)}
              className="text-xs p-2 rounded-xl border border-slate-300 bg-white font-semibold cursor-pointer"
            >
              {availableModels.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </div>
        </div>

        {asrResult ? (
          <div className="space-y-4">
            {/* Top Score Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">
                  {t.eval.werLabel}
                </span>
                <p className="text-2xl font-black text-slate-900">
                  {(asrResult.overall_wer * 100).toFixed(1)}%
                </p>
                <p className="text-[11px] text-slate-500 mt-1">{t.eval.werDesc}</p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">
                  {t.eval.cerLabel}
                </span>
                <p className="text-2xl font-black text-slate-900">
                  {(asrResult.overall_cer * 100).toFixed(1)}%
                </p>
                <p className="text-[11px] text-slate-500 mt-1">{t.eval.cerDesc}</p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">
                  {t.eval.exactMatchLabel}
                </span>
                <p className="text-2xl font-black text-emerald-600">
                  {(asrResult.exact_match_rate * 100).toFixed(1)}%
                </p>
                <p className="text-[11px] text-slate-500 mt-1">{t.eval.exactMatchDesc}</p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">
                  {t.eval.latencyLabel}
                </span>
                <p className="text-2xl font-black text-indigo-600">
                  {asrResult.avg_latency_sec}s
                </p>
                <p className="text-[11px] text-slate-500 mt-1">{t.eval.latencyDesc}</p>
              </div>
            </div>

            {/* Category Breakdown Table (Standard vs Varhadi vs Code-Switched) */}
            {asrResult.category_metrics && (
              <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm overflow-hidden">
                <div className="p-4 bg-slate-50 border-b border-slate-200">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    {t.eval.categoryBreakdownTitle}
                  </h3>
                </div>
                <div className="divide-y divide-slate-100">
                  {Object.entries(asrResult.category_metrics).map(([cat, met]: [string, any]) => (
                    <div key={cat} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <span className="text-sm font-bold text-slate-900">{cat}</span>
                        <p className="text-xs text-slate-500">
                          {t.eval.samplesCount}: {met.sample_count}
                        </p>
                      </div>
                      <div className="flex items-center space-x-6 text-xs">
                        <div>
                          <span className="text-slate-400 block font-medium">WER</span>
                          <strong className="text-slate-800 text-sm">{(met.wer * 100).toFixed(1)}%</strong>
                        </div>
                        <div>
                          <span className="text-slate-400 block font-medium">CER</span>
                          <strong className="text-slate-800 text-sm">{(met.cer * 100).toFixed(1)}%</strong>
                        </div>
                        <div>
                          <span className="text-slate-400 block font-medium">{t.eval.exactMatchLabel}</span>
                          <strong className="text-emerald-600 text-sm">{(met.exact_match_rate * 100).toFixed(1)}%</strong>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white p-8 rounded-3xl border border-slate-200 text-center space-y-3">
            <BarChart3 className="w-10 h-10 text-slate-300 mx-auto" />
            <h3 className="text-sm font-bold text-slate-700">{t.eval.noDataTitle}</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {t.eval.noDataDesc}
            </p>
          </div>
        )}
      </div>

      {/* Section 2: RAG Retrieval Benchmark */}
      <div className="space-y-4 pt-4 border-t border-slate-200">
        <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
          <Activity className="w-5 h-5 text-indigo-600" />
          <span>{t.eval.ragSectionTitle}</span>
        </h2>

        {ragResult && ragResult.status === 'success' ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">
                  {t.eval.recallLabel}
                </span>
                <p className="text-2xl font-black text-indigo-600">
                  {(ragResult.recall_at_k * 100).toFixed(1)}%
                </p>
                <p className="text-[11px] text-slate-500 mt-1">{t.eval.recallDesc}</p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">
                  {t.eval.precisionLabel}
                </span>
                <p className="text-2xl font-black text-slate-900">
                  {(ragResult.precision_at_k * 100).toFixed(1)}%
                </p>
                <p className="text-[11px] text-slate-500 mt-1">{t.eval.precisionDesc}</p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">
                  {t.eval.mrrLabel}
                </span>
                <p className="text-2xl font-black text-emerald-600">
                  {ragResult.mrr.toFixed(3)}
                </p>
                <p className="text-[11px] text-slate-500 mt-1">{t.eval.mrrDesc}</p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm">
                <span className="text-[11px] font-bold text-slate-500 uppercase block mb-1">
                  {t.eval.suppressionLabel}
                </span>
                <p className="text-2xl font-black text-purple-600">
                  {(ragResult.unsupported_claim_suppression * 100).toFixed(0)}%
                </p>
                <p className="text-[11px] text-slate-500 mt-1">{t.eval.suppressionDesc}</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white p-8 rounded-3xl border border-slate-200 text-center space-y-3">
            <Activity className="w-10 h-10 text-slate-300 mx-auto" />
            <h3 className="text-sm font-bold text-slate-700">{t.eval.noDataTitle}</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {t.eval.noDataDesc}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
