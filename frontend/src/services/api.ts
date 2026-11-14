import axios from 'axios';
import {
  TranscriptionResponse,
  KnowledgeBaseStats,
  CorpusSourcesResponse,
  SystemHealth
} from '../types';

const API_BASE = '/api';

export const apiClient = {
  // Speech API
  async transcribeAudio(file: Blob, language: string = 'mr', engine?: string): Promise<TranscriptionResponse> {
    const formData = new FormData();
    formData.append('audio', file, 'recording.webm');
    formData.append('language', language);
    if (engine) formData.append('engine', engine);

    const res = await axios.post(`${API_BASE}/speech/transcribe`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  async getAsrModels() {
    const res = await axios.get(`${API_BASE}/speech/models`);
    return res.data;
  },

  async selectAsrModel(modelName: string) {
    const formData = new FormData();
    formData.append('model_name', modelName);
    const res = await axios.post(`${API_BASE}/speech/select-model`, formData);
    return res.data;
  },

  // Translation & Dialect
  async translateText(text: string, srcLang: string = 'mr', tgtLang: string = 'en') {
    const res = await axios.post(`${API_BASE}/translation/translate`, {
      text,
      src_lang: srcLang,
      tgt_lang: tgtLang
    });
    return res.data;
  },

  async normalizeDialect(text: string) {
    const res = await axios.post(`${API_BASE}/translation/normalize-dialect`, { text });
    return res.data;
  },

  // Chat API
  async sendChatMessage(query: string, language: string = 'mr', conversationId?: string, voiceOutput: boolean = true) {
    const res = await axios.post(`${API_BASE}/chat`, {
      query,
      language,
      conversation_id: conversationId,
      voice_output: voiceOutput
    });
    return res.data;
  },

  async sendVoiceChat(file: Blob, language: string = 'mr', conversationId?: string, voiceOutput: boolean = true) {
    const formData = new FormData();
    formData.append('audio', file, 'voice_query.webm');
    formData.append('language', language);
    if (conversationId) formData.append('conversation_id', conversationId);
    formData.append('voice_output', String(voiceOutput));

    const res = await axios.post(`${API_BASE}/chat/voice`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  async getConversations() {
    const res = await axios.get(`${API_BASE}/chat/conversations`);
    return res.data;
  },

  // Documents & RAG API
  async getDocuments(): Promise<KnowledgeBaseStats> {
    const res = await axios.get(`${API_BASE}/documents`);
    return res.data;
  },

  /** Public list of the official documents the knowledge base is built from. */
  async getCorpusSources(): Promise<CorpusSourcesResponse> {
    const res = await axios.get(`${API_BASE}/documents/sources`);
    return res.data;
  },

  async uploadDocument(file: File, title?: string, issuingAuthority?: string) {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    if (issuingAuthority) formData.append('issuing_authority', issuingAuthority);

    const res = await axios.post(`${API_BASE}/documents/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  async deleteDocument(docId: string) {
    const res = await axios.delete(`${API_BASE}/documents/${docId}`);
    return res.data;
  },

  async reindexDocuments() {
    const res = await axios.post(`${API_BASE}/documents/reindex`);
    return res.data;
  },

  // Feedback API
  async submitFeedback(messageId: string, rating: number, correction?: string, notes?: string) {
    const res = await axios.post(`${API_BASE}/feedback`, {
      message_id: messageId,
      rating,
      correction,
      feedback_notes: notes
    });
    return res.data;
  },

  // Evaluation API
  async getEvaluationSummary() {
    const res = await axios.get(`${API_BASE}/evaluation/summary`);
    return res.data;
  },

  async runAsrBenchmark(modelName?: string) {
    const formData = new FormData();
    if (modelName) formData.append('model_name', modelName);
    const res = await axios.post(`${API_BASE}/evaluation/run-asr`, formData);
    return res.data;
  },

  async runRagBenchmark() {
    const res = await axios.post(`${API_BASE}/evaluation/run-rag`);
    return res.data;
  },

  // System Health
  async getHealth(): Promise<SystemHealth> {
    const res = await axios.get(`${API_BASE}/health`);
    return res.data;
  }
};

