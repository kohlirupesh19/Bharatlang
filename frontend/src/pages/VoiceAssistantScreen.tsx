import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Play, Pause, Edit3, Send, AlertTriangle, RefreshCw, Volume2, Upload, FileAudio, Check, Sparkles } from 'lucide-react';
import { apiClient } from '../services/api';
import { TranscriptionResponse } from '../types';
import { getTranslation } from '../i18n/translations';
import { dialectLabel } from '../utils/dialectLabel';

interface VoiceAssistantScreenProps {
  onSubmitQueryToChat: (query: string, language: string) => void;
  selectedLanguage: string;
}

export const VoiceAssistantScreen: React.FC<VoiceAssistantScreenProps> = ({
  onSubmitQueryToChat,
  selectedLanguage
}) => {
  const t = getTranslation(selectedLanguage);

  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [transcription, setTranscription] = useState<TranscriptionResponse | null>(null);
  const [editableTranscript, setEditableTranscript] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<any>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Timer for recording duration
  useEffect(() => {
    if (isRecording) {
      setRecordingDuration(0);
      timerRef.current = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording]);

  // Stop the microphone if the user leaves this screen mid-recording.
  useEffect(() => {
    return () => {
      const recorder = mediaRecorderRef.current;
      if (recorder && recorder.state !== 'inactive') {
        recorder.onstop = null;
        recorder.stop();
      }
      recorder?.stream.getTracks().forEach((track) => track.stop());
    };
  }, []);

  // Release the previous recording's object URL when it is replaced or the screen closes.
  useEffect(() => {
    return () => {
      if (recordedAudioUrl) URL.revokeObjectURL(recordedAudioUrl);
    };
  }, [recordedAudioUrl]);

  const startRecording = async () => {
    setErrorMsg(null);
    setTranscription(null);
    setRecordedAudioUrl(null);
    setAudioBlob(null);
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const audioUrl = URL.createObjectURL(audioBlob);
        setAudioBlob(audioBlob);
        setRecordedAudioUrl(audioUrl);
        // Automatically process transcription
        handleTranscribe(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err: any) {
      setErrorMsg(t.voice.micPermissionError);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
    }
  };

  const handleTranscribe = async (blob: Blob) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const result = await apiClient.transcribeAudio(blob, selectedLanguage);
      setTranscription(result);
      setEditableTranscript(result.recognized_text);
    } catch (err: unknown) {
      console.warn('Transcription failed:', err);
      setErrorMsg(t.voice.requestFailed);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setRecordedAudioUrl(url);
      setAudioBlob(file);
      handleTranscribe(file);
    }
    e.target.value = ''; // allow choosing the same file again
  };

  const handleSubmit = () => {
    const finalQuery = editableTranscript.trim();
    if (finalQuery) {
      onSubmitQueryToChat(finalQuery, selectedLanguage);
    }
  };

  const handleReprocess = async () => {
    if (!editableTranscript.trim()) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const normalized = await apiClient.normalizeDialect(editableTranscript);
      if (transcription) {
        setTranscription({
          ...transcription,
          normalized_text: normalized.normalized_text,
          detected_dialect: normalized.dialect,
          dialect_replacements: normalized.replacements
        });
      }
    } catch (err: unknown) {
      console.warn('Re-checking the transcript failed:', err);
      setErrorMsg(t.voice.requestFailed);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Title */}
      <div className="text-center space-y-2">
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
          {t.voice.title}
        </h1>
        <p className="text-xs sm:text-sm text-slate-600 max-w-xl mx-auto leading-relaxed">
          {t.voice.subtitle}
        </p>
      </div>

      {/* Main Voice Recording Card */}
      <div className="bg-white rounded-3xl p-8 border border-slate-200/90 shadow-md flex flex-col items-center justify-center space-y-6">
        {/* Waveform / Visualizer State */}
        <div className="h-16 flex items-center justify-center space-x-1 w-full max-w-xs">
          {isRecording ? (
            Array.from({ length: 16 }).map((_, i) => (
              <div
                key={i}
                className="w-1.5 bg-indigo-600 rounded-full wave-bar"
                style={{
                  height: `${Math.max(10, Math.sin(i + recordingDuration) * 36)}px`,
                  animationDelay: `${(i * 0.08).toFixed(2)}s`
                }}
              />
            ))
          ) : (
            <div className="text-xs text-slate-400 font-medium flex items-center space-x-1.5">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span>{t.voice.subtitle}</span>
            </div>
          )}
        </div>

        {/* Large Microphone Action Button */}
        <div className="relative">
          {isRecording && (
            <div className="absolute inset-0 rounded-full bg-red-400 animate-ping opacity-30" />
          )}
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isLoading}
            className={`w-28 h-28 rounded-full flex flex-col items-center justify-center transition-all shadow-xl relative z-10 ${
              isRecording
                ? 'bg-red-600 hover:bg-red-700 text-white scale-105 ring-4 ring-red-200'
                : 'bg-gradient-to-tr from-indigo-600 to-indigo-800 hover:from-indigo-700 hover:to-indigo-900 text-white hover:scale-105 active:scale-95'
            } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {isRecording ? (
              <>
                <Square className="w-8 h-8 fill-current mb-1" />
                <span className="text-xs font-bold uppercase tracking-wider">{t.voice.recordStop}</span>
              </>
            ) : (
              <>
                <Mic className="w-10 h-10 mb-1" />
                <span className="text-xs font-bold uppercase tracking-wider">{t.voice.recordStart}</span>
              </>
            )}
          </button>
        </div>

        {/* Duration / Status Counter */}
        <div className="flex items-center space-x-3 text-sm">
          {isRecording ? (
            <span className="font-mono text-red-600 font-bold bg-red-50 px-3 py-1 rounded-full border border-red-200">
              {t.voice.recordingTime}: {formatDuration(recordingDuration)}
            </span>
          ) : (
            recordedAudioUrl && (
              <span className="font-mono text-slate-600 bg-slate-100 px-3 py-1 rounded-full">
                {t.voice.recordingLength}: {formatDuration(transcription?.duration_sec ? Math.round(transcription.duration_sec) : recordingDuration)}
              </span>
            )
          )}
        </div>

        {/* Secondary: Upload File option */}
        <div className="pt-2 border-t border-slate-100 w-full flex items-center justify-center">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept="audio/*,.wav,.mp3,.webm,.m4a"
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="text-xs font-semibold text-slate-600 hover:text-indigo-600 flex items-center space-x-1.5 px-4 py-2 rounded-xl hover:bg-slate-100 transition-all border border-slate-200"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>{t.voice.uploadAudio}</span>
          </button>
        </div>

        {/* Audio Player if recording exists */}
        {recordedAudioUrl && (
          <div className="w-full max-w-md bg-slate-50 p-3 rounded-2xl border border-slate-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileAudio className="w-4 h-4 text-indigo-600" />
              <span className="text-xs font-medium text-slate-700">{t.voice.yourRecording}</span>
            </div>
            <audio ref={audioPlayerRef} src={recordedAudioUrl} controls className="h-8 max-w-[200px]" />
          </div>
        )}
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-2xl text-sm flex items-center space-x-2 shadow-xs">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="bg-indigo-50 border border-indigo-200 p-6 rounded-2xl flex items-center justify-center space-x-3 text-indigo-700 shadow-xs">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span className="text-sm font-semibold">
            {t.voice.processing}
          </span>
        </div>
      )}

      {/* Interactive Transcript Editor Card */}
      {transcription && !isLoading && (
        <div className="bg-white rounded-3xl p-6 sm:p-7 border border-slate-200/90 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center space-x-2">
              <Edit3 className="w-5 h-5 text-indigo-600" />
              <h2 className="text-base font-bold text-slate-900">
                {t.voice.previewTitle}
              </h2>
            </div>
            {/* Dialect Badge */}
            {dialectLabel(transcription.detected_dialect, t) && (
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                {dialectLabel(transcription.detected_dialect, t)}
              </span>
            )}
          </div>

          {/* Plain notice when recognition is uncertain (the backend's own wording stays in the API) */}
          {transcription.is_uncertain && (
            <div className="bg-amber-50 border border-amber-200 p-3 rounded-xl text-xs text-amber-800 flex items-start space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <p>{t.voice.uncertainNotice}</p>
            </div>
          )}

          {/* Raw Recognized Transcript vs Editable */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">
              {t.voice.editTranscript}:
            </label>
            <textarea
              value={editableTranscript}
              onChange={(e) => setEditableTranscript(e.target.value)}
              rows={3}
              className="w-full text-base p-3.5 rounded-2xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-sans shadow-inner"
              placeholder={t.voice.editTranscript}
            />
          </div>

          {/* Non-destructive Normalization Info */}
          {transcription.dialect_replacements && transcription.dialect_replacements.length > 0 && (
            <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 text-xs space-y-2">
              <span className="font-bold text-slate-700 block">{t.voice.understoodAs}:</span>
              <p className="text-slate-800 font-medium bg-white p-2.5 rounded-xl border border-slate-200">
                {transcription.normalized_text}
              </p>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {transcription.dialect_replacements.map((r, i) => (
                  <span key={i} className="bg-white px-2 py-0.5 rounded-lg border border-slate-200 text-slate-600">
                    <span className="line-through text-slate-400">{r.original}</span> → <span className="font-bold text-indigo-600">{r.normalized}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Metadata Bar & Actions */}
          <div className="flex flex-wrap items-center justify-end text-xs text-slate-500 pt-3 border-t border-slate-100">
            {/* Action Buttons */}
            <div className="flex items-center space-x-2">
              <button
                onClick={handleReprocess}
                className="px-3.5 py-2 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-100 font-semibold text-xs flex items-center space-x-1.5 transition-all"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>{t.voice.saveEdit}</span>
              </button>
              <button
                onClick={handleSubmit}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center space-x-1.5 shadow-md shadow-indigo-600/20 transition-all hover:scale-[1.02]"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{t.voice.submitToChat}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
