import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'

import { api } from '../../../api/client'
import { ShortfallWorkspace } from './ShortfallWorkspace'
import fixture from './repair.fixture.json'

function mount() {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter initialEntries={[`/dispatch/shortfalls/${fixture.id}`]}>
        <Routes>
          <Route path="/dispatch/shortfalls/:id" element={<ShortfallWorkspace />} />
          <Route path="/dispatch/plan" element={<p>Published plan</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

it('test_br28_recommends_without_auto_applying_and_br29_labels_store_rule', async () => {
  vi.spyOn(api, 'GET').mockResolvedValue({ data: fixture } as never)
  const post = vi.spyOn(api, 'POST')
  mount()
  expect(await screen.findByRole('radio', { name: 'Option A' })).toHaveAttribute(
    'aria-checked',
    'true',
  )
  expect(screen.getByText('Breaks TESTOUT2’s rule')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Call the dock' })).toBeDisabled()
  expect(post).not.toHaveBeenCalled()
})

it('test_br30_publishes_only_the_human_selected_option', async () => {
  vi.spyOn(api, 'GET').mockResolvedValue({ data: fixture } as never)
  const post = vi
    .spyOn(api, 'POST')
    .mockResolvedValue({ data: { operating_date: fixture.operating_date } } as never)
  mount()
  fireEvent.click(await screen.findByRole('radio', { name: 'Option B' }))
  fireEvent.click(screen.getByRole('button', { name: 'Apply B · publish v2' }))
  await waitFor(() =>
    expect(post).toHaveBeenCalledWith('/api/v1/shortfalls/{shortfall_id}/apply', {
      params: { path: { shortfall_id: fixture.id } },
      body: { option_id: fixture.options[1]!.id },
    }),
  )
  expect(await screen.findByText('Published plan')).toBeVisible()
})

it('test_br28_no_feasible_repair_keeps_apply_disabled', async () => {
  vi.spyOn(api, 'GET').mockResolvedValue({ data: { ...fixture, options: [] } } as never)
  mount()
  expect(
    await screen.findByText('No feasible repair is available. Review the hold with the dock.'),
  ).toBeVisible()
  expect(screen.getByRole('button', { name: 'Apply — · publish v2' })).toBeDisabled()
})
