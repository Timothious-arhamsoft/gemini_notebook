import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import { authApi } from '../../../../api/auth'
import { useAuth } from '../../../../contexts/AuthContext'
import { Button } from '../../../../components/Button'
import type { RegisterPayload } from '../../../../types'
import {
  FULL_NAME_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  USERNAME_MAX_LENGTH,
  USERNAME_MIN_LENGTH,
  formatAuthApiError,
  validateRegisterForm,
} from '../../../../utils/authValidation'

export function RegisterForm({ onSwitch }: { onSwitch: () => void }) {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<RegisterPayload>({
    email: '',
    username: '',
    full_name: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    const clientError = validateRegisterForm(form)
    if (clientError) {
      setError(clientError)
      return
    }

    // Normalize identity fields to match backend; never trim/alter password
    const payload: RegisterPayload = {
      full_name: form.full_name.trim(),
      username: form.username.trim().toLowerCase(),
      email: form.email.trim().toLowerCase(),
      password: form.password,
    }

    setLoading(true)
    try {
      const user = await authApi.register(payload)
      // Auto-login with normalized email from the API when available
      const tokens = await authApi.login({
        email: user.email || payload.email,
        password: payload.password,
      })
      await login(tokens.access_token)
      navigate('/dashboard')
    } catch (err: unknown) {
      const detail = isAxiosError(err) ? err.response?.data?.detail : undefined
      setError(formatAuthApiError(detail, 'Registration failed. Try again.'))
    } finally {
      setLoading(false)
    }
  }

  const set = (k: keyof RegisterPayload) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <div className="auth-form__header">
        <h1 className="auth-form__title">Create an account</h1>
        <p className="auth-form__subtitle">Start building your AI notebook</p>
      </div>

      {error && <div className="auth-form__error">{error}</div>}

      <div className="auth-form__fields">
        <label className="auth-form__label">
          Full name
          <input
            className="auth-form__input"
            type="text"
            placeholder="Tim"
            value={form.full_name}
            onChange={set('full_name')}
            required
            maxLength={FULL_NAME_MAX_LENGTH}
            autoComplete="name"
            autoFocus
          />
        </label>
        <label className="auth-form__label">
          Username
          <input
            className="auth-form__input"
            type="text"
            placeholder="timgill"
            value={form.username}
            onChange={set('username')}
            required
            minLength={USERNAME_MIN_LENGTH}
            maxLength={USERNAME_MAX_LENGTH}
            pattern="[A-Za-z0-9_]+"
            title="Letters, numbers, and underscores only"
            autoComplete="username"
          />
        </label>
        <label className="auth-form__label">
          Email
          <input
            className="auth-form__input"
            type="email"
            placeholder="you@example.com"
            value={form.email}
            onChange={set('email')}
            required
            autoComplete="email"
          />
        </label>
        <label className="auth-form__label">
          Password
          <input
            className="auth-form__input"
            type="password"
            placeholder="••••••••"
            value={form.password}
            onChange={set('password')}
            required
            minLength={PASSWORD_MIN_LENGTH}
            autoComplete="new-password"
          />
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
