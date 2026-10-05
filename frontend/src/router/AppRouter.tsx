import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../contexts/AuthContext'
import { ProtectedRoute, PublicRoute } from './guards'
import { Home } from '../pages/Home'
import { Auth } from '../pages/Auth'
import { Dashboard } from '../pages/Dashboard'
import { Notebook } from '../pages/Notebook'

export function AppRouter() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Landing page — always visible */}
          <Route path="/" element={<Home />} />

          {/* Public-only routes — redirect to /dashboard if already logged in */}
          <Route element={<PublicRoute />}>
            <Route path="/auth"     element={<Auth />} />
            <Route path="/login"    element={<Navigate to="/auth" replace />} />
            <Route path="/register" element={<Navigate to="/auth" replace />} />
          </Route>

          {/* Protected routes — redirect to /auth if not logged in */}
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/notebook/:id" element={<Notebook />} />
          </Route>

          {/* 404 fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}