import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { Home } from '../pages/Home'
import { Auth } from '../pages/Auth'
import { Dashboard } from '../pages/Dashboard'
// import { Notebook } from '../pages/Notebook'

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />

        <Route path="/login" element={<Auth />} />
        <Route path="/register" element={<Auth />} />

        <Route path="/dashboard" element={<Dashboard />} />

        {/* <Route path="/notebook/:id" element={<Notebook />} /> */}

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  )
}