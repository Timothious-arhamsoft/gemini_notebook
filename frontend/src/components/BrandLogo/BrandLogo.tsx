import notegenioIcon from '../../assets/notegenio_icon.png'
import './BrandLogo.css'

interface BrandLogoProps {
  /** Icon size in pixels. Default 22. */
  size?: number
  showText?: boolean
  className?: string
  textClassName?: string
}

export function BrandLogo({
  size = 22,
  showText = true,
  className = '',
  textClassName = '',
}: BrandLogoProps) {
  return (
    <span className={`brand-logo${className ? ` ${className}` : ''}`}>
      <img
        src={notegenioIcon}
        alt=""
        width={size}
        height={size}
        className="brand-logo__icon"
        decoding="async"
        aria-hidden="true"
      />
      {showText && (
        <span className={`brand-logo__text${textClassName ? ` ${textClassName}` : ''}`}>
          NoteGenio
        </span>
      )}
    </span>
  )
}
