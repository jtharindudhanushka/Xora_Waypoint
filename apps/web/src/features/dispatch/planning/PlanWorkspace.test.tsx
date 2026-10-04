import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from '../../../api/client'
import { PlanWorkspace } from './PlanWorkspace'
import fixture from './planning.fixture.json'

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <PlanWorkspace />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('Dispatcher planning (BR-20–23)', () => {
  it('test_br21_requires_a_written_reason_for_a_repeat_deferral', async () => {
    const plan = structuredClone(fixture.plan)
    plan.deferrals[0]!.repeat_skip = true
    vi.spyOn(api, 'GET').mockImplementation(
      async (url: string) =>
        ({
          data: url.includes('/fleet') ? fixture.fleet : plan,
          response: new Response(),
        }) as never,
    )
    const post = vi
      .spyOn(api, 'POST')
      .mockResolvedValue({ data: plan, response: new Response() } as never)
    mount()
    fireEvent.click(await screen.findByRole('button', { name: 'Deferred · 4' }))
    expect(screen.getByLabelText('Confirm TESTDEFER1')).not.toBeChecked()
    fireEvent.click(screen.getByLabelText('Confirm TESTDEFER1'))
    fireEvent.change(screen.getByLabelText('Reason for another deferral'), {
      target: { value: 'No feasible reefer remains' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm 4 deferrals' }))
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith(
        '/api/v1/plan-versions/{version_id}/deferrals/confirm',
        expect.objectContaining({
          body: {
            items: expect.arrayContaining([
              { deferral_id: 'defer-1', reason: 'No feasible reefer remains' },
            ]),
          },
        }),
      ),
    )
  })

  it('test_br22_hard_publish_gate_disables_commit_and_renders_readable_violation', async () => {
    Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
      configurable: true,
      value: function (this: HTMLDialogElement) {
        this.setAttribute('open', '')
      },
    })
    vi.spyOn(api, 'GET').mockImplementation(
      async (url: string) =>
        ({
          data: url.includes('publish-check')
            ? {
                can_publish: false,
                violations: [
                  {
                    rule_id: 'BR-06',
                    code: 'WEIGHT',
                    message: 'TESTV01 trip 1: weight 1,096 / 1,040 kg',
                    context: {},
                  },
                ],
                unconfirmed_deferrals: [],
                late_risk_order_refs: [],
              }
            : url.includes('/fleet')
              ? fixture.fleet
              : fixture.plan,
          response: new Response(),
        }) as never,
    )
    mount()
    fireEvent.click(await screen.findByRole('button', { name: 'Review & publish' }))
    expect(await screen.findByText('TESTV01 trip 1: weight 1,096 / 1,040 kg')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Publish plan v1' })).toBeDisabled()
  })

  it('test_br10_workshop_vehicle_cannot_be_switched_on', async () => {
    const fleet = structuredClone(fixture.fleet)
    fleet[0]!.status = 'workshop'
    fleet[0]!.switched_on = false
    vi.spyOn(api, 'GET').mockImplementation(
      async (url: string) =>
        ({
          data: url.includes('/fleet') ? fleet : fixture.plan,
          response: new Response(),
        }) as never,
    )
    mount()
    fireEvent.click(await screen.findByRole('button', { name: 'Fleet · 7 of 7' }))
    expect(screen.getByRole('switch', { name: 'Include TESTV01' })).toBeDisabled()
  })
})
