import './Spinner.css'

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function Spinner({ size = 'md', className = '' }: SpinnerProps) {
  return <span className={`spinner spinner--${size} ${className}`} aria-label="Loading" />
}
