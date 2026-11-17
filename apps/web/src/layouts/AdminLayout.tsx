import { Outlet, useLocation } from 'react-router-dom';
import { AdminSidebar } from '../components/navigation/AdminSidebar';
import { Badge } from '../components/common/Badge';

export function AdminLayout() {
  const location = useLocation();

  // Create friendly title from path
  const currentPathSegment = location.pathname.split('/').filter(Boolean).pop() || 'Dashboard';
  const pageTitle = currentPathSegment
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  return (
    <div className="min-h-screen flex bg-surface-base text-slate-100">
      {/* Sidebar */}
      <AdminSidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-16 border-b border-surface-border px-8 flex items-center justify-between bg-surface-elevated/40 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 font-mono">ADMIN CONSOLE</span>
            <span className="text-slate-600">/</span>
            <span className="text-sm font-semibold text-slate-200">{pageTitle}</span>
          </div>

          <div className="flex items-center gap-3">
            <Badge variant="purple" dot>
              Role: System Architect
            </Badge>
            <Badge variant="brand">
              Phase 1
            </Badge>
          </div>
        </header>

        {/* Dynamic Route Content */}
        <main className="flex-1 p-8 overflow-y-auto bg-grid-pattern">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
