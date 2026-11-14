import { lazy, Suspense, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { Navbar } from './components/Navbar';
import { HomeScreen } from './pages/HomeScreen';
import { VoiceAssistantScreen } from './pages/VoiceAssistantScreen';
import { ChatAssistantScreen } from './pages/ChatAssistantScreen';
import { DocumentsScreen } from './pages/DocumentsScreen';
import { getTranslation } from './i18n/translations';
import { useServiceStatus } from './hooks/useServiceStatus';
import { useAdminRoute } from './hooks/useAdminRoute';
import type { ScreenId } from './types';

// Operator screens load as separate chunks, so their technical wording and controls
// are not part of the citizen bundle.
const KnowledgeBaseAdminScreen = lazy(() =>
  import('./pages/admin/KnowledgeBaseAdminScreen').then((m) => ({ default: m.KnowledgeBaseAdminScreen }))
);
const EvaluationScreen = lazy(() =>
  import('./pages/admin/EvaluationScreen').then((m) => ({ default: m.EvaluationScreen }))
);

const HTML_LANG: Record<string, string> = { mr: 'mr', 'mr-varhadi': 'mr', hi: 'hi', en: 'en' };

const ADMIN_SCREENS: ReadonlySet<ScreenId> = new Set<ScreenId>(['kbAdmin', 'eval']);

export function App() {
  const [activeScreen, setActiveScreen] = useState<ScreenId>('home');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('mr');
  const [passedChatQuery, setPassedChatQuery] = useState<string>('');
  const serviceStatus = useServiceStatus();
  const isAdmin = useAdminRoute();

  const t = getTranslation(selectedLanguage);

  useEffect(() => {
    document.documentElement.lang = HTML_LANG[selectedLanguage] ?? 'mr';
  }, [selectedLanguage]);

  // Leaving /#admin while on an operator screen returns to the home page.
  useEffect(() => {
    if (!isAdmin && ADMIN_SCREENS.has(activeScreen)) setActiveScreen('home');
  }, [isAdmin, activeScreen]);

  const handleSelectSampleQuery = (query: string) => {
    setPassedChatQuery(query);
    setActiveScreen('chat');
  };

  const handleSubmitFromVoice = (query: string, language: string) => {
    setSelectedLanguage(language);
    setPassedChatQuery(query);
    setActiveScreen('chat');
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      <Navbar
        activeScreen={activeScreen}
        setActiveScreen={setActiveScreen}
        selectedLanguage={selectedLanguage}
        setSelectedLanguage={setSelectedLanguage}
        serviceStatus={serviceStatus}
        showAdmin={isAdmin}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {activeScreen === 'home' && (
          <HomeScreen
            onNavigate={setActiveScreen}
            serviceStatus={serviceStatus}
            onSelectSampleQuery={handleSelectSampleQuery}
            selectedLanguage={selectedLanguage}
          />
        )}

        {activeScreen === 'voice' && (
          <VoiceAssistantScreen
            onSubmitQueryToChat={handleSubmitFromVoice}
            selectedLanguage={selectedLanguage}
          />
        )}

        {activeScreen === 'chat' && (
          <ChatAssistantScreen
            initialQuery={passedChatQuery}
            selectedLanguage={selectedLanguage}
            onInitialQueryConsumed={() => setPassedChatQuery('')}
          />
        )}

        {activeScreen === 'docs' && <DocumentsScreen selectedLanguage={selectedLanguage} />}

        {isAdmin && ADMIN_SCREENS.has(activeScreen) && (
          <Suspense
            fallback={
              <div className="flex justify-center py-16 text-indigo-600">
                <RefreshCw className="w-6 h-6 animate-spin" />
              </div>
            }
          >
            {activeScreen === 'kbAdmin' && <KnowledgeBaseAdminScreen selectedLanguage={selectedLanguage} />}
            {activeScreen === 'eval' && <EvaluationScreen selectedLanguage={selectedLanguage} />}
          </Suspense>
        )}
      </main>

      <footer className="bg-slate-900 border-t border-slate-800 text-slate-400 text-xs py-5 px-6 text-center">
        <p className="max-w-4xl mx-auto leading-relaxed">{t.footer.text}</p>
      </footer>
    </div>
  );
}

export default App;
