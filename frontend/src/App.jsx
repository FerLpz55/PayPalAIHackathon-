import { useCallback, useRef, useState } from 'react'
import CustomerHeader from './components/layout/CustomerHeader.jsx'
import Sidebar from './components/layout/Sidebar.jsx'
import Toast from './components/layout/Toast.jsx'
import Topbar from './components/layout/Topbar.jsx'
import { useDemoData } from './hooks/useDemoData.js'
import { useHashRoute } from './hooks/useHashRoute.js'
import AccountingPage from './pages/AccountingPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import OrderDetailPage from './pages/OrderDetailPage.jsx'
import OrdersPage from './pages/OrdersPage.jsx'
import QuotesPage from './pages/QuotesPage.jsx'
import ReceiptsPage from './pages/ReceiptsPage.jsx'
import OrderTrackingPage from './pages/customer/OrderTrackingPage.jsx'
import PaymentReturnPage from './pages/customer/PaymentReturnPage.jsx'
import QuoteReviewPage from './pages/customer/QuoteReviewPage.jsx'
import RequestOrderPage from './pages/customer/RequestOrderPage.jsx'
import EmptyState from './components/ui/EmptyState.jsx'
import LoadingState from './components/ui/LoadingState.jsx'
import WorkshopLogin from './components/auth/WorkshopLogin.jsx'
import { useWorkshopSession } from './hooks/useWorkshopSession.js'
import { isConfigurationMissing } from './services/apiClient.js'
import './styles/app.css'

function App() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const menuTriggerRef = useRef(null)
  const closeNav = useCallback(() => setMobileNavOpen(false), [])
  const { route, query, go } = useHashRoute(closeNav)
  const isCustomer = route.startsWith('customer/')
  const quoteId = route === 'customer/quote' ? new URLSearchParams(query).get('id') : null
  const requiresWorkshopAuth = !isCustomer && !isConfigurationMissing
  const auth = useWorkshopSession({ enabled: requiresWorkshopAuth })
  const dataEnabled = !requiresWorkshopAuth || auth.status === 'authenticated'
  const { orders, quote, loading, notice, error, refresh, mutate, dismiss } = useDemoData({
    customerMode: isCustomer,
    quoteId,
    enabled: dataEnabled,
  })
  const shared = { orders, quote, loading, go, mutate, refresh, error }

  const renderPage = () => {
    if (route === 'customer/payment/return') return <PaymentReturnPage go={go} refresh={refresh} />
    if (route === 'customer/payment/cancel') return <PaymentReturnPage cancelled go={go} refresh={refresh} />
    if (route === 'customer/quote') return <QuoteReviewPage {...shared} />
    if (route === 'customer/tracking') return <OrderTrackingPage {...shared} />
    if (isCustomer) return <RequestOrderPage {...shared} />
    if (route === 'orders') return <OrdersPage {...shared} />
    if (route === 'quotes') return <QuotesPage {...shared} />
    if (route === 'receipts') return <ReceiptsPage {...shared} />
    if (route === 'accounting') return <AccountingPage {...shared} />
    if (route.startsWith('order/')) return <OrderDetailPage id={route.split('/')[1]} {...shared} />
    return <DashboardPage {...shared} />
  }

  return (
    <div className={`${isCustomer ? 'app customer-app' : 'app'}${isConfigurationMissing ? ' app-unconfigured' : ''}`}>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      {!isCustomer && !isConfigurationMissing && (!requiresWorkshopAuth || auth.status === 'authenticated') && <Sidebar active={route.split('/')[0]} open={mobileNavOpen} onClose={closeNav} go={go} triggerRef={menuTriggerRef} />}
      <div className="main-area">
        {isConfigurationMissing
          ? <header className="topbar"><div className="brand"><span className="brand-mark" aria-hidden="true">T</span><span>TallerClaro</span></div></header>
          : isCustomer ? <CustomerHeader /> : <Topbar route={route} onMenu={() => setMobileNavOpen((open) => !open)} menuOpen={mobileNavOpen} menuButtonRef={menuTriggerRef} username={auth.username} onLogout={auth.status === 'authenticated' ? auth.logout : undefined} />}
        <Toast error={error} notice={notice} onDismiss={dismiss} />
        <main id="main-content" tabIndex="-1" inert={mobileNavOpen}>{isConfigurationMissing
          ? <div className={isCustomer ? 'customer-page' : 'page-content'}><EmptyState title="Application mode is not configured" text="Set VITE_API_BASE_URL to connect to the backend. To use sample data, explicitly set VITE_APP_MODE=demo. Sample data is hidden until DEMO is selected." /></div>
          : (requiresWorkshopAuth && auth.status === 'checking') || auth.status === 'signing_out'
            ? <div className="page-content"><LoadingState /></div>
            : requiresWorkshopAuth && (auth.status === 'anonymous' || auth.status === 'error')
              ? <WorkshopLogin onLogin={auth.login} initialError={auth.error} />
              : renderPage()}</main>
      </div>
    </div>
  )
}

export default App
