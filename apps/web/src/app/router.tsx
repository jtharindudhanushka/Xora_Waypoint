import { Navigate, createBrowserRouter } from 'react-router-dom'

import { LoginPage } from '../features/auth/LoginPage'
import { StoreShell } from '../features/store/StoreShell'
import { StoreHome } from '../features/store/StoreHome'
import { NewOrder } from '../features/store/NewOrder'
import { ReceiptPage } from '../features/store/Receipt'
import { ReportProblem } from '../features/store/ReportProblem'
import { DeliveryNotice } from '../features/store/DeliveryNotice'
import { DockPage, DockShell, DockTripPage } from '../features/dock/DockPage'
import { PlanWorkspace } from '../features/dispatch/planning/PlanWorkspace'
import { ShortfallWorkspace } from '../features/dispatch/repair/ShortfallWorkspace'
import { LiveOpsWorkspace } from '../features/dispatch/ops/LiveOpsWorkspace'
import { IssueWorkspace } from '../features/dispatch/issues/IssueWorkspace'
import { OutcomePage } from '../features/driver/OutcomePage'
import { RecordPage, UploadsPage } from '../features/driver/RecordPage'
import { StopPage } from '../features/driver/StopPage'
import { DriverShell, TripPage } from '../features/driver/TripPage'
import { DesktopShell } from './DesktopShell'
import { HomeRedirect, RequireRole } from './guards'

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
      { path: 'issues/:id', element: <IssueWorkspace /> },
      {
        path: 'plan',
        element: <PlanWorkspace />,
      },
      {
        path: 'ops',
        element: <LiveOpsWorkspace />,
      },
    ],
  },
  {
    path: '/dock',
    element: (
      <RequireRole role="loader">
        <DockShell />
      </RequireRole>
    ),
    children: [
      { index: true, element: <DockPage /> },
      { path: 'trips/:id', element: <DockTripPage /> },
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
