import { Bot, Mic, MessageSquare, BookOpen, FolderCog, ClipboardCheck, Globe } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { getTranslation } from '../i18n/translations';
import type { ScreenId, ServiceStatus } from '../types';
import { ServiceStatusBadge } from './ServiceStatusBadge';

interface NavbarProps {
  activeScreen: ScreenId;
  setActiveScreen: (screen: ScreenId) => void;
  selectedLanguage: string;
  setSelectedLanguage: (lang: string) => void;
  serviceStatus: ServiceStatus;
  /** Show the operator screens (only on `/#admin`). */
  showAdmin: boolean;
}

interface NavItem {
  id: ScreenId;
  label: string;
  icon: LucideIcon;
}

export function Navbar({
  activeScreen,
  setActiveScreen,
  selectedLanguage,
  setSelectedLanguage,
  serviceStatus,
  showAdmin
}: NavbarProps) {
  const t = getTranslation(selectedLanguage);

  const citizenItems: NavItem[] = [
    { id: 'home', label: t.nav.home, icon: Bot },
    { id: 'voice', label: t.nav.voice, icon: Mic },
    { id: 'chat', label: t.nav.chat, icon: MessageSquare },
    { id: 'docs', label: t.nav.docs, icon: BookOpen }
  ];
  const adminItems: NavItem[] = [
    { id: 'kbAdmin', label: t.nav.manageDocs, icon: FolderCog },
    { id: 'eval', label: t.nav.qualityChecks, icon: ClipboardCheck }
  ];
  const navItems = showAdmin ? [...citizenItems, ...adminItems] : citizenItems;

  const renderItem = (item: NavItem, compact: boolean) => {
    const Icon = item.icon;
    const isActive = activeScreen === item.id;
    const base = compact
      ? 'flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all'
      : 'flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-semibold transition-all';
    const state = isActive
      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
      : compact
        ? 'text-slate-300 bg-slate-800/80'
        : 'text-slate-300 hover:text-white hover:bg-slate-800/80';
    return (
      <button
        key={item.id}
        onClick={() => setActiveScreen(item.id)}
        aria-current={isActive ? 'page' : undefined}
        className={`${base} ${state}`}
      >
        <Icon className={compact ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
        <span>{item.label}</span>
      </button>
    );
  };

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-50 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between min-h-[70px] py-2 gap-3">
          {/* Logo & Product Brand */}
          <button
            type="button"
            className="flex items-center space-x-3 cursor-pointer select-none group text-left"
            onClick={() => setActiveScreen('home')}
          >
            <img
              src="/logo.png"
              alt=""
              width={40}
              height={40}
              className="w-10 h-10 rounded-xl shadow-lg shadow-orange-500/20 ring-2 ring-white/10 group-hover:scale-105 transition-transform shrink-0"
            />
            <div className="flex flex-col justify-center">
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg sm:text-xl tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent">
                  BharatLangTech AI
                </span>
                <span className="hidden sm:inline text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                  {t.nav.dialectBadge}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium hidden sm:block leading-none mt-1">
                {t.nav.tagline}
              </p>
            </div>
          </button>

          {/* Navigation Pills (Desktop) */}
          <nav className="hidden md:flex items-center space-x-1.5 bg-slate-950/60 p-1.5 rounded-2xl border border-slate-800/80">
            {navItems.map((item) => renderItem(item, false))}
          </nav>

          {/* Right Controls: plain service status & language selector */}
          <div className="flex items-center space-x-3">
            <ServiceStatusBadge status={serviceStatus} t={t} />

            <div className="relative flex items-center">
              <div className="absolute left-2.5 pointer-events-none text-indigo-400">
                <Globe className="w-3.5 h-3.5" />
              </div>
              <select
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                aria-label="भाषा निवडा (Select Language)"
                className="bg-slate-800 hover:bg-slate-750 border border-slate-700 text-white text-xs rounded-xl pl-8 pr-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-semibold cursor-pointer shadow-sm transition-all"
              >
                <option value="mr">मराठी (Marathi)</option>
                <option value="mr-varhadi">वऱ्हाडी (Varhadi - Vidarbha)</option>
                <option value="hi">हिंदी (Hindi)</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Navigation bar */}
      <div className="md:hidden flex overflow-x-auto px-2 py-2 border-t border-slate-800 space-x-1.5 scrollbar-none bg-slate-950">
        {navItems.map((item) => renderItem(item, true))}
      </div>
    </header>
  );
}
