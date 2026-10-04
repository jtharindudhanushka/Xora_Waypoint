import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'outline' | 'danger'
type Size = 'md' | 'lg'

const VARIANTS: Record<Variant, string> = {
  // Orange only when something needs attention (design direction); dark text on orange (AA).
  primary: 'bg-brand text-on-brand hover:bg-brand-hover',
  secondary: 'bg-inverse text-on-inverse hover:opacity-90',
  outline: 'border border-line-strong bg-surface text-primary hover:bg-sunken',
  danger: 'bg-[var(--danger-solid)] text-[var(--text-on-danger)] hover:opacity-90',
}

// 44 px on desktop; 56 px for primary field actions on phones and tablets.
const SIZES: Record<Size, string> = { md: 'h-11 px-5 text-sm', lg: 'h-14 px-6 text-base' }

export function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition disabled:cursor-not-allowed disabled:bg-disabled disabled:text-[var(--text-disabled)] ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...props}
    />
  )
}
