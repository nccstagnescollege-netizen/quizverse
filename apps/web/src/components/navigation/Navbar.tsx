import { Link, useLocation } from 'react-router-dom';
import { Layers, Shield, Sparkles, KeyRound } from 'lucide-react';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { useApiHealth } from '../../hooks/useStatus';

export function Navbar() {
  const location = useLocation();
  const { data: health, isLoading } = useApiHealth();

  const isCurrent = (path: string) => location.pathname === path;

  return (
    <header className="sticky top-0 z-50 glass-nav border-b border-surface-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 via-cyber-purple to-cyber-cyan p-0.5 shadow-glow-primary group-hover:scale-105 transition-transform duration-200">
              <div className="w-full h-full bg-surface-base rounded-[10px] flex items-center justify-center">
                <Layers className="w-5 h-5 text-cyber-cyan" />
              </div>
            </div>
            <div>
              <span className="font-display font-extrabold text-lg tracking-wider text-white">
                QUIZ<span className="text-cyber-cyan">VERSE</span>
              </span>
              <span className="block text-[10px] text-slate-400 tracking-widest uppercase font-mono">
                3D Exam Engine
              </span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-6">
            <Link
              to="/"
              className={`text-sm font-medium transition-colors ${
                isCurrent('/') ? 'text-cyber-cyan' : 'text-slate-300 hover:text-white'
              }`}
            >
              Overview
            </Link>
            <Link
              to="/exam/demo-test"
              className={`text-sm font-medium transition-colors flex items-center gap-1.5 ${
                location.pathname.startsWith('/exam')
                  ? 'text-cyber-cyan'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              Exam Portal
            </Link>
            <Link
              to="/admin/dashboard"
              className={`text-sm font-medium transition-colors flex items-center gap-1.5 ${
                location.pathname.startsWith('/admin')
                  ? 'text-brand-400'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <Shield className="w-3.5 h-3.5" />
              Admin Portal
            </Link>
          </nav>

          {/* Right Action / System Status */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:block">
              {isLoading ? (
                <Badge variant="neutral" dot>
                  API Connecting
                </Badge>
              ) : health?.status === 'healthy' ? (
                <Badge variant="emerald" dot>
                  API Online
                </Badge>
              ) : (
                <Badge variant="rose" dot>
                  API Standby
                </Badge>
              )}
            </div>

            <Link to="/login">
              <Button variant="cyber" size="sm" className="gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
