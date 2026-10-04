/** Exact exported Figma assets; intrinsic SVG dimensions are preserved. */
const ASSETS = {
  arrow: '7aa20.svg',
  arrowDark: '2dfb9.svg',
  chevron: '42d8b.svg',
  clock: '92280.svg',
  snowflake: 'e601d.svg',
  alertSmall: '415b6.svg',
  close: '27fcb.svg',
  lock: '442f8.svg',
  info: '5b0ef.svg',
  checkWhite: 'a6c6e.svg',
  check: 'eef42.svg',
  alert: 'af399.svg',
  pause: '102e0.svg',
  home: '18bd0.svg',
} as const

export function FigmaIcon({ name }: { name: keyof typeof ASSETS }) {
  return <img alt="" src={`/figma/${ASSETS[name]}`} className="shrink-0 max-w-none" />
}
