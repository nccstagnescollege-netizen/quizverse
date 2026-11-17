import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  HelpCircle,
  BookOpen,
  Settings,
  Layers,
  ArrowLeft,
  ShieldCheck,
} from 'lucide-react';

const ADMIN_LINKS = [
  {
    label: 'Dashboard',
    href: '/admin/dashboard',
    icon: LayoutDashboard,
    badge: 'v1.0',
  },
  {
    label: 'Question Bank',
    href: '/admin/question-bank',
    icon: HelpCircle,
  },
  {
    label: 'Quizzes & Exams',
    href: '/admin/quizzes',
    icon: BookOpen,
  },
  {
    label: 'Settings',
    href: '/admin/settings',
    icon: Settings,
  },
];

export function AdminSidebar() {
  const location = useLocation();

  return (
    <aside className="w-64 border-r border-surface-border bg-surface-base/80 backdrop-blur-xl flex flex-col h-screen sticky top-0">
      {/* Brand */}
      <div className="p-6 border-b border-surface-border flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center shadow-glow-primary">
            <Layers className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="font-display font-bold text-sm text-white">QUIZVERSE</span>
            <span className="block text-[10px] text-brand-400 font-mono">ADMIN SUITE</span>
          </div>
        </Link>
        <span title="Administrator Access">
          <ShieldCheck className="w-4 h-4 text-brand-400" />
        </span>
      </div>

      {/* Nav List */}
      <nav className="p-4 space-y-1.5 flex-1">
        <p className="px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
          Management
        </p>
        {ADMIN_LINKS.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.href;
          return (
            <Link
              key={item.href}
              to={item.href}
              className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-600 text-white shadow-glow-primary'
                  : 'text-slate-300 hover:text-white hover:bg-surface-elevated'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded ${
                    isActive ? 'bg-white/20 text-white' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer / Back to site */}
      <div className="p-4 border-t border-surface-border">
        <Link
          to="/"
          className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors rounded-lg hover:bg-surface-elevated"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Public Portal
        </Link>
      </div>
    </aside>
  );
}
