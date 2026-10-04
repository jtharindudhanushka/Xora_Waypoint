import { Navigate, createBrowserRouter } from 'react-router-dom'

import { LoginPage } from '../features/auth/LoginPage'
import { RoleHome } from '../features/placeholder/RoleHome'
import { PlanWorkspace } from '../features/dispatch/planning/PlanWorkspace'
import { ShortfallWorkspace } from '../features/dispatch/repair/ShortfallWorkspace'
import { OutcomePage } from '../features/driver/OutcomePage'
import { RecordPage, UploadsPage } from '../features/driver/RecordPage'
import { StopPage } from '../features/driver/StopPage'
import { DriverShell, TripPage } from '../features/driver/TripPage'
import { DesktopShell } from './DesktopShell'
import { HomeRedirect, RequireRole } from './guards'
import { PhoneShell } from './PhoneShell'

export const router = createBrowserRouter([
  { path: '/', element: <HomeRedirect /> },
  { path: '/login', element: <LoginPage /> },
  {
    path: '/dispatch',
    element: (
      <RequireRole role="dispatcher">
        <DesktopShell />
      </RequireRole>
    ),
    children: [
      { index: true, element: <Navigate to="plan" replace /> },
      { path: 'shortfalls/:id', element: <ShortfallWorkspace /> },
      {
        path: 'plan',
        element: <PlanWorkspace />,
      },
      {
        path: 'ops',
        element: (
          <RoleHome
            title="Live operations"
            screens={['D5 Live ops', 'D10 Store report', 'D13 Reconcile']}
          />
        ),
      },
    ],
  },
  {
    path: '/dock',
    element: (
      <RequireRole role="loader">
        <PhoneShell tabs={[{ to: '/dock', label: 'Trips' }]} />
      </RequireRole>
    ),
    children: [
      {
        index: true,
        element: (
          <RoleHome
            title="Loading trips"
            screens={[
              'L1 Trips',
              'L2 Load trip',
              'L3 Report shortfall',
              'L4 On hold',
              'L5 Review revision',
            ]}
          />
        ),
      },
    ],
  },
  {
    path: '/driver',
    element: (
      <RequireRole role="driver">
        <DriverShell />
      </RequireRole>
    ),
    children: [
      { index: true, element: <TripPage /> },
      { path: 'stops/:id', element: <StopPage /> },
      { path: 'stops/:id/outcome', element: <OutcomePage /> },
      { path: 'records/:eventId', element: <RecordPage /> },
      { path: 'uploads', element: <UploadsPage /> },
    ],
  },
  {
    path: '/store',
    element: (
      <RequireRole role="store_manager">
        <PhoneShell tabs={[{ to: '/store', label: 'Home' }]} />
      </RequireRole>
    ),
    children: [
      {
        index: true,
        element: (
          <RoleHome
            title="Home"
            screens={[
              'S1 Home + tracking',
              'S2 New order',
              'S5 Confirm receipt',
              'S6 Report a problem',
              'S8 Deferral notice',
            ]}
          />
        ),
      },
    ],
  },
  { path: '*', element: <HomeRedirect /> },
])
