import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileText, Trash2, RefreshCw, CheckCircle, AlertTriangle, Layers, BookOpen } from 'lucide-react';
import { apiClient } from '../../services/api';
import { KnowledgeBaseStats, DocumentItem } from '../../types';
import { getAdminTranslation } from '../../i18n/adminTranslations';

interface KnowledgeBaseAdminScreenProps {
  selectedLanguage: string;
}

export const KnowledgeBaseAdminScreen: React.FC<KnowledgeBaseAdminScreenProps> = ({ selectedLanguage }) => {
  const t = getAdminTranslation(selectedLanguage);

  const [kbData, setKbData] = useState<KnowledgeBaseStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Upload Form state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [customTitle, setCustomTitle] = useState('');
  const [issuingAuthority, setIssuingAuthority] = useState('महाराष्ट्र शासन कृषी विभाग');

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const data = await apiClient.getDocuments();
      setKbData(data);
    } catch (err: any) {
      setErrorMsg('Error retrieving documents.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setErrorMsg('Only PDF documents (.pdf) are supported.');
        return;
      }
      setUploadFile(file);
      if (!customTitle) {
        setCustomTitle(file.name.replace('.pdf', ''));
      }
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    setIsUploading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await apiClient.uploadDocument(uploadFile, customTitle, issuingAuthority);
      setSuccessMsg(`'${customTitle || uploadFile.name}' indexed successfully.`);
      setUploadFile(null);
      setCustomTitle('');
      if (fileInputRef.current) fileInputRef.current.value = '';
      await fetchDocuments();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Document upload and indexing failed.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId: string, title: string) => {
    if (!window.confirm(`Delete document '${title}'?`)) return;

    try {
      await apiClient.deleteDocument(docId);
      setSuccessMsg(`'${title}' deleted.`);
      await fetchDocuments();
    } catch (err: any) {
      setErrorMsg('Failed to delete document.');
    }
  };

  const handleReindex = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await apiClient.reindexDocuments();
      setSuccessMsg('Knowledge base index rebuilt successfully.');
      await fetchDocuments();
    } catch (err: any) {
      setErrorMsg('Reindexing failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            {t.kb.title}
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-1">
            {t.kb.subtitle}
          </p>
        </div>
        <button
          onClick={handleReindex}
          disabled={isLoading}
          className="flex items-center space-x-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-bold shadow-md transition-all self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>{isLoading ? t.kb.rebuilding : t.kb.rebuildBtn}</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">{t.kb.statsTotalDocs}</span>
            <p className="text-2xl font-black text-slate-900">{kbData?.total_documents || 0}</p>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-sm flex items-center space-x-4">
          <div className="w-12 h-12 rounded-xl bg-purple-50 flex items-center justify-center text-purple-600">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">{t.kb.statsTotalChunks}</span>
            <p className="text-2xl font-black text-slate-900">{kbData?.index_stats.total_chunks || 0}</p>
          </div>
        </div>
      </div>

      {/* Success / Error Alerts */}
      {successMsg && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-2xl text-sm flex items-center space-x-2 shadow-xs">
          <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}
      {errorMsg && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-2xl text-sm flex items-center space-x-2 shadow-xs">
          <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Upload Form Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 border border-slate-200/90 shadow-sm">
        <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center space-x-2">
          <Upload className="w-5 h-5 text-indigo-600" />
          <span>{t.kb.uploadHeader}</span>
        </h2>

        <form onSubmit={handleUploadSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                {t.kb.titleLabel} *
              </label>
              <input
                type="text"
                required
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
                placeholder="e.g. Namo Shetkari Yojana GR"
                className="w-full text-sm p-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                {t.kb.authorityLabel}
              </label>
              <input
                type="text"
                value={issuingAuthority}
                onChange={(e) => setIssuingAuthority(e.target.value)}
                placeholder="e.g. Government of Maharashtra"
                className="w-full text-sm p-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
              {t.kb.fileLabel} *
            </label>
            <input
              type="file"
              ref={fileInputRef}
              required
              accept=".pdf"
              onChange={handleFileSelect}
              className="w-full text-xs text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer border border-slate-300 rounded-xl p-1"
            />
          </div>

          <button
            type="submit"
            disabled={!uploadFile || isUploading}
            className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold text-xs flex items-center space-x-2 shadow-md shadow-indigo-600/20 transition-all cursor-pointer"
          >
            <Upload className="w-4 h-4" />
            <span>{isUploading ? t.kb.uploading : t.kb.uploadBtn}</span>
          </button>
        </form>
      </div>

      {/* Indexed Documents Table */}
      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-sm overflow-hidden">
        <div className="p-5 bg-slate-50 border-b border-slate-200">
          <h2 className="text-sm font-bold text-slate-800">
            {t.kb.indexedListHeader}
          </h2>
        </div>

        {kbData?.documents && kbData.documents.length > 0 ? (
          <div className="divide-y divide-slate-100">
            {kbData.documents.map((doc: DocumentItem) => (
              <div key={doc.id} className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50 transition-colors">
                <div className="flex items-start space-x-3">
                  <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600 shrink-0">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 leading-snug">{doc.title}</h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {doc.issuing_authority} • {doc.chunk_count} chunks • {doc.file_size_kb} KB
                    </p>
                    <span className="inline-block font-mono text-[11px] text-slate-400 mt-0.5">
                      {doc.filename}
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(doc.id, doc.title)}
                  className="self-end sm:self-center p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all"
                  title={t.kb.docDelete}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-400 text-xs">
            {t.kb.emptyList}
          </div>
        )}
      </div>
    </div>
  );
};
