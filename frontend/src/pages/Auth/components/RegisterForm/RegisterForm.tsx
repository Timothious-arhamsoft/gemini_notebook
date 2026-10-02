import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../../../../api/auth'
import { useAuth } from '../../../../contexts/AuthContext'
import { Button } from '../../../../components/Button'
import type { RegisterPayload } from '../../../../types'

export function RegisterForm({ onSwitch }: { onSwitch: () => void }) {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<RegisterPayload>({ email: '', username: '', full_name: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.register(form)
      // Auto-login after register
      const tokens = await authApi.login({ email: form.email, password: form.password })
      await login(tokens.access_token)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Try again.')
    } finally {
      setLoading(false)
    }
  }

  const set = (k: keyof RegisterPayload) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <div className="auth-form__header">
        <h1 className="auth-form__title">Create an account</h1>
        <p className="auth-form__subtitle">Start building your AI notebook</p>
      </div>

      {error && <div className="auth-form__error">{error}</div>}

      <div className="auth-form__fields">
        <label className="auth-form__label">
          Full name
          <input className="auth-form__input" type="text" placeholder="Tim Cook"
            value={form.full_name} onChange={set('full_name')} autoFocus />
        </label>
        <label className="auth-form__label">
          Username
          <input className="auth-form__input" type="text" placeholder="timcook"
            value={form.username} onChange={set('username')} required />
        </label>
        <label className="auth-form__label">
          Email
          <input className="auth-form__input" type="email" placeholder="you@example.com"
            value={form.email} onChange={set('email')} required />
        </label>
        <label className="auth-form__label">
          Password
          <input className="auth-form__input" type="password" placeholder="••••••••"
            value={form.password} onChange={set('password')} required minLength={6} />
        </label>
      </div>

      <Button type="submit" size="lg" loading={loading} className="auth-form__submit">
        Create account
      </Button>

      <p className="auth-form__switch">
        Already have an account?{' '}
        <button type="button" className="auth-form__link" onClick={onSwitch}>
          Sign in
        </button>
      </p>
    </form>
  )
}
