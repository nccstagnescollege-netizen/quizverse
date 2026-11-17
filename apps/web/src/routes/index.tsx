import { Routes, Route, Navigate } from 'react-router-dom';
import { PublicLayout } from '../layouts/PublicLayout';
import { AdminLayout } from '../layouts/AdminLayout';
import { LandingPage } from '../pages/public/LandingPage';
import { LoginPage } from '../pages/public/LoginPage';
import { ExamTokenPage } from '../pages/public/ExamTokenPage';
import { AdminDashboardPage } from '../pages/admin/AdminDashboardPage';
import { AdminQuestionBankPage } from '../pages/admin/AdminQuestionBankPage';
import { AdminQuizzesPage } from '../pages/admin/AdminQuizzesPage';
import { AdminSettingsPage } from '../pages/admin/AdminSettingsPage';
import { NotFoundPage } from '../pages/NotFoundPage';

export function AppRoutes() {
  return (
    <Routes>
      {/* Public Pages */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/exam/:token" element={<ExamTokenPage />} />
      </Route>

      {/* Admin Pages */}
      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<Navigate to="/admin/dashboard" replace />} />
        <Route path="dashboard" element={<AdminDashboardPage />} />
        <Route path="question-bank" element={<AdminQuestionBankPage />} />
        <Route path="quizzes" element={<AdminQuizzesPage />} />
        <Route path="settings" element={<AdminSettingsPage />} />
      </Route>

      {/* Catch-all 404 */}
      <Route element={<PublicLayout />}>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
