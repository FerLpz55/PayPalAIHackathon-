import { useCallback, useEffect, useRef, useState } from 'react'
import CustomerHeader from './components/layout/CustomerHeader.jsx'
import Sidebar from './components/layout/Sidebar.jsx'
import Toast from './components/layout/Toast.jsx'
import Topbar from './components/layout/Topbar.jsx'
import WorkshopSignInDialog from './components/layout/WorkshopSignInDialog.jsx'
import Button from './components/ui/Button.jsx'
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
import { isConfigurationMissing, isDemoMode } from './services/apiClient.js'
import { clearWorkshopCredentials, getWorkshopCredentials } from './services/sessionStore.js'
import './styles/app.css'

function App() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [signInOpen, setSignInOpen] = useState(false)
  const [workshopAuthenticated, setWorkshopAuthenticated] = useState(() => Boolean(getWorkshopCredentials()))
  const [authRevision, setAuthRevision] = useState(0)
  const menuTriggerRef = useRef(null)
  const closeNav = useCallback(() => setMobileNavOpen(false), [])
  const { route, query, go } = useHashRoute(closeNav)
  const isCustomer = route.startsWith('customer/')
  const quoteId = route === 'customer/quote' ? new URLSearchParams(query).get('id') : null
  const workshopDataEnabled = isCustomer || isDemoMode || isConfigurationMissing || workshopAuthenticated
  const { orders, quote, loading, notice, error, refresh, mutate, dismiss } = useDemoData({ customerMode: isCustomer, quoteId, enabled: workshopDataEnabled, authScope: authRevision })
  const shared = { orders, quote, loading, go, mutate, refresh, error }

  useEffect(() => {
    const handleAuthLost = () => {
      setWorkshopAuthenticated(false)
      setAuthRevision((value) => value + 1)
    }
    window.addEventListener('tallerclaro:workshop-auth-lost', handleAuthLost)
    return () => window.removeEventListener('tallerclaro:workshop-auth-lost', handleAuthLost)
  }, [])

  const handleSignedIn = () => {
    setWorkshopAuthenticated(true)
    setAuthRevision((value) => value + 1)
    setSignInOpen(false)
  }

  const handleSignedOut = () => {
    clearWorkshopCredentials()
    setWorkshopAuthenticated(false)
    setAuthRevision((value) => value + 1)
  }

  const renderPage = () => {
    if (!isCustomer && !isDemoMode && !isConfigurationMissing && !workshopAuthenticated) {
      return <div className="page-content"><EmptyState title="Sign in to your workshop" text="Workshop orders and financial data stay hidden until you verify access. No sample data is shown in REAL mode." action={<Button onClick={() => setSignInOpen(true)}>Sign in</Button>} /></div>
    }
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
      {!isCustomer && !isConfigurationMissing && <Sidebar active={route.split('/')[0]} open={mobileNavOpen} onClose={closeNav} go={go} triggerRef={menuTriggerRef} />}
      <div className="main-area">
        {isConfigurationMissing
          ? <header className="topbar"><div className="brand"><span className="brand-mark" aria-hidden="true">T</span><span>TallerClaro</span></div></header>
          : isCustomer ? <CustomerHeader /> : <Topbar route={route} onMenu={() => setMobileNavOpen((open) => !open)} menuOpen={mobileNavOpen} menuButtonRef={menuTriggerRef} workshopAuthenticated={workshopAuthenticated} onSignIn={() => setSignInOpen(true)} onSignOut={handleSignedOut} />}
        <Toast error={error} notice={notice} onDismiss={dismiss} />
        <main key={authRevision} id="main-content" tabIndex="-1" inert={mobileNavOpen}>{isConfigurationMissing
          ? <div className={isCustomer ? 'customer-page' : 'page-content'}><EmptyState title="Application mode is not configured" text="Set VITE_API_BASE_URL to connect to the backend. To use sample data, explicitly set VITE_APP_MODE=demo. Sample data is hidden until DEMO is selected." /></div>
          : renderPage()}</main>
      </div>
      {signInOpen && !isDemoMode && <WorkshopSignInDialog onClose={() => setSignInOpen(false)} onSignedIn={handleSignedIn} />}
    </div>
  )
}

export default App
