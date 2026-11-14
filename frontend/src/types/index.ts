export type LanguageCode = 'mr' | 'mr-varhadi' | 'hi' | 'en';

export interface SourceCitation {
  document_id: string;
  document_title: string;
  page: number;
  similarity_score: number;
  excerpt: string;
}

export interface DialectReplacement {
  original: string;
  normalized: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  original_text: string;
  normalized_text?: string;
  detected_dialect?: string;
  dialect_replacements?: DialectReplacement[];
  answer?: string;
  english_translation?: string;
  sources?: SourceCitation[];
  audio_url?: string;
  latency_ms?: number;
  created_at: string;
  is_uncertain?: boolean;
  /** Set on the local placeholder shown when the request failed (no feedback/translate). */
  is_error?: boolean;
}

export interface ASRSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  confidence?: number;
}

export interface TranscriptionResponse {
  audio_identifier: string;
  recognized_text: string;
  normalized_text: string;
  detected_language: string;
  detected_dialect: string;
  dialect_replacements: DialectReplacement[];
  overall_confidence: number | null;
  is_uncertain: boolean;
  warning_message: string | null;
  duration_sec: number;
  processing_latency_sec: number;
  model_name: string;
  segments: ASRSegment[];
}

export interface DocumentItem {
  id: string;
  title: string;
  filename: string;
  issuing_authority?: string;
  publication_date?: string;
  upload_date?: string;
  processing_status: 'pending' | 'indexed' | 'failed';
  chunk_count: number;
  file_size_kb: number;
  error_message?: string;
}

export interface KnowledgeBaseStats {
  total_documents: number;
  index_stats: {
    total_vectors: number;
    total_chunks: number;
    indexed_documents_count: number;
  };
  documents: DocumentItem[];
}

/** One official document the knowledge base is built from (GET /api/documents/sources). */
export interface CorpusSource {
  doc_id: string;
  title: string;
  gr_number: string | null;
  department: string | null;
  issue_date: string | null;
  language: string | null;
  status: 'current' | 'superseded';
  url: string | null;
}

export interface CorpusSourcesResponse {
  total: number;
  documents: CorpusSource[];
}

/** Citizen screens, plus the two operator screens shown only on `/#admin`. */
export type ScreenId = 'home' | 'voice' | 'chat' | 'docs' | 'kbAdmin' | 'eval';

/** What the citizen UI shows about the backend: plain words, no technical detail. */
export type ServiceStatus = 'checking' | 'available' | 'unavailable';

export interface SystemHealth {
  status: string;
  platform: string;
  hardware: {
    cuda_available: boolean;
    mps_available: boolean;
    active_device: string;
    system_total_memory_gb: number;
    system_available_memory_gb: number;
    memory_percent_used: number;
  };
  services: {
    llm: {
      provider: 'ollama' | 'bedrock';
      configured_model: string;
      endpoint: string;
      is_running: boolean;
    };
    asr_engine: {
      active_engine: string;
      available_engines: string[];
      loaded_engines: string[];
    };
    rag_knowledge_base: {
      total_chunks: number;
      indexed_documents_count: number;
    };
    tts_voice: string;
  };
}

