import { Outlet } from 'react-router-dom';
import { Navbar } from '../components/navigation/Navbar';

export function PublicLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-surface-base text-slate-100 bg-grid-pattern relative">
      {/* Background ambient lighting */}
      <div className="fixed inset-0 pointer-events-none bg-radial-glow z-0" />

      {/* Main Navbar */}
      <Navbar />

      {/* Page Content */}
      <main className="flex-1 relative z-10">
        <Outlet />
      </main>

      {/* Futuristic Public Footer */}
      <footer className="border-t border-surface-border bg-surface-base/90 py-8 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <span className="font-semibold text-slate-300">QUIZVERSE</span>
            <span>&bull;</span>
            <span>Advanced 3D Examination Platform</span>
            <span>&bull;</span>
            <span className="font-mono text-xs text-cyber-cyan">Phase 1 Foundation</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-slate-400 font-mono">
            <span>React + Vite</span>
            <span>Three.js / R3F</span>
            <span>Hono API</span>
            <span>Supabase</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
