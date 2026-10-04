import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import { LoginPage } from './LoginPage'

describe('LoginPage (X1)', () => {
  it('lists the four demo accounts and fills the form when one is picked', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )
    expect(screen.getAllByRole('listitem')).toHaveLength(4)
    fireEvent.click(screen.getByText('Driver · VEH036'))
    expect(screen.getByLabelText('Work email')).toHaveValue('driver.veh036@waypoint.demo')
    expect(screen.getByLabelText('Password')).toHaveValue('demo1234')
  })
})
