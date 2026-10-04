import type { InputHTMLAttributes } from 'react'
import { FigmaIcon } from './FigmaIcon'

/** Figma's 22 px square selection; native input keeps keyboard and form semantics. */
export function Checkbox({ className = '', ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className={`relative inline-flex size-[22px] shrink-0 ${className}`}>
      <input
        {...props}
        type="checkbox"
        className="peer absolute inset-0 z-10 size-full cursor-pointer opacity-0 disabled:cursor-not-allowed"
      />
      <span
        aria-hidden="true"
        className="flex size-[22px] items-center justify-center rounded-sm border border-line-strong bg-surface peer-checked:border-[var(--bg-inverse)] peer-checked:bg-inverse peer-focus-visible:outline-2 peer-focus-visible:outline-brand"
      >
        {props.checked && <FigmaIcon name="checkWhite" />}
      </span>
    </label>
  )
}
