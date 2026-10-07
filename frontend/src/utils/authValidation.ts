/** Client-side registration checks aligned with backend/app/auth_validation.py */

export const USERNAME_MIN_LENGTH = 3
export const USERNAME_MAX_LENGTH = 100
export const FULL_NAME_MAX_LENGTH = 255
export const PASSWORD_MIN_LENGTH = 6

const USERNAME_PATTERN = /^[A-Za-z0-9_]+$/
/** Structural email check only — no DNS/MX/domain existence. */
const EMAIL_STRUCTURE_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function isValidEmailSyntax(email: string): boolean {
  const trimmed = email.trim()
  if (!trimmed) return false
  if (trimmed.includes('@@')) return false
  return EMAIL_STRUCTURE_RE.test(trimmed)
}

export function validateRegisterForm(input: {
  full_name: string
  username: string
  email: string
  password: string
}): string | null {
  const fullName = input.full_name.trim()
  if (!fullName) return 'Please enter your full name.'
  if (fullName.length > FULL_NAME_MAX_LENGTH) {
    return `Full name must be at most ${FULL_NAME_MAX_LENGTH} characters.`
  }

  const username = input.username.trim()
  if (!username) return 'Please enter a username.'
  if (username.length < USERNAME_MIN_LENGTH || username.length > USERNAME_MAX_LENGTH) {
    return `Username must be between ${USERNAME_MIN_LENGTH} and ${USERNAME_MAX_LENGTH} characters.`
  }
  if (!USERNAME_PATTERN.test(username)) {
    return 'Username may only contain letters, numbers, and underscores.'
  }

  const email = input.email.trim().toLowerCase()
  if (!email || !isValidEmailSyntax(email)) {
    return 'Please enter a valid email address.'
  }

  // Do not trim password — whitespace may be intentional
  if (!input.password) {
    return `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`
  }
  if (input.password.trim() === '') {
    return 'Password cannot be only whitespace.'
  }
  if (input.password.length < PASSWORD_MIN_LENGTH) {
    return `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`
  }

  return null
}

/**
 * Normalize FastAPI `detail` (string or validation error list) for display.
 */
export function formatAuthApiError(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim()) return detail

  if (Array.isArray(detail) && detail.length > 0) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) {
          const msg = String((item as { msg: unknown }).msg)
          return msg.replace(/^Value error,\s*/i, '').trim()
        }
        return null
      })
      .filter((m): m is string => !!m)

    if (messages.length > 0) return messages[0]
  }

  return fallback
}
