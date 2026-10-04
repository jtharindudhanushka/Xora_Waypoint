import { Navigate, createBrowserRouter } from 'react-router-dom'

import { LoginPage } from '../features/auth/LoginPage'
import { StoreShell } from '../features/store/StoreShell'
import { StoreHome } from '../features/store/StoreHome'
import { NewOrder } from '../features/store/NewOrder'
import { ReceiptPage } from '../features/store/Receipt'
import { ReportProblem } from '../features/store/ReportProblem'
import { DeliveryNotice } from '../features/store/DeliveryNotice'
import { RoleHome } from '../features/placeholder/RoleHome'
import { PlanWorkspace } from '../features/dispatch/planning/PlanWorkspace'
import { ShortfallWorkspace } from '../features/dispatch/repair/ShortfallWorkspace'
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
        <PhoneShell
          tabs={[
            { to: '/driver', label: 'Trip' },
            { to: '/driver/uploads', label: 'Uploads' },
          ]}
        />
      </RequireRole>
    ),
    children: [
      {
        index: true,
        element: (
          <RoleHome title="Today’s trip" screens={['R1 Trip', 'R2 Stop', 'R3 Record outcome']} />
        ),
      },
      {
        path: 'uploads',
        element: (
          <RoleHome
            title="Uploads"
            screens={['R4 Saved offline', 'R5 Uploaded', 'R7 Needs review']}
          />
        ),
      },
    ],
  },
  {
    path: '/store',
    element: (
      <RequireRole role="store_manager">
        <StoreShell />
      </RequireRole>
    ),
    children: [
      { index: true, element: <StoreHome /> },
      { path: 'orders/new', element: <NewOrder /> },
      { path: 'orders/:ref/receipt', element: <ReceiptPage /> },
      { path: 'orders/:ref/issue', element: <ReportProblem /> },
      { path: 'notices/:id', element: <DeliveryNotice /> },
    ],
  },
  { path: '*', element: <HomeRedirect /> },
])
