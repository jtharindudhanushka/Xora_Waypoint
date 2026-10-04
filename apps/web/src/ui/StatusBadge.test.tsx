import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatusBadge } from './StatusBadge'

describe('StatusBadge (BR-54)', () => {
  it('always shows a text label, never colour alone', () => {
    render(<StatusBadge status="pending_sync" />)
    expect(screen.getByText('Pending sync')).toBeInTheDocument()
  })

  it('accepts a custom label for the same status style', () => {
    render(<StatusBadge status="deferred" label="Moved to Wed" />)
    expect(screen.getByText('Moved to Wed')).toBeInTheDocument()
  })
})
