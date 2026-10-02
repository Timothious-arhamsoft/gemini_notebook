import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../../../../api/auth'
import { useAuth } from '../../../../contexts/AuthContext'
import { Button } from '../../../../components/Button'
import type { LoginPayload } from '../../../../types'

export function LoginForm({ onSwitch }: { onSwitch: () => void }) {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<LoginPayload>({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const tokens = await authApi.login(form)
      await login(tokens.access_token)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <div className="auth-form__header">
        <h1 className="auth-form__title">Welcome back</h1>
        <p className="auth-form__subtitle">Sign in to your Gemini Notebook</p>
      </div>

      {error && <div className="auth-form__error">{error}</div>}

      <div className="auth-form__fields">
        <label className="auth-form__label">
          Email
          <input
            className="auth-form__input"
            type="email"
            placeholder="you@example.com"
            value={form.email}
            onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
            required
            autoFocus
          />
        </label>

        <label className="auth-form__label">
          Password
          <input
            className="auth-form__input"
            type="password"
            placeholder="••••••••"
            value={form.password}
            onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
            required
          />
        </label>
      </div>

      <Button type="submit" size="lg" loading={loading} className="auth-form__submit">
        Sign in
      </Button>

      <p className="auth-form__switch">
        Don't have an account?{' '}
        <button type="button" className="auth-form__link" onClick={onSwitch}>
          Create one
        </button>
      </p>
    </form>
  )
}
