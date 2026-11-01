import { useCallback, useState } from 'react'
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
import QuoteReviewPage from './pages/customer/QuoteReviewPage.jsx'
import RequestOrderPage from './pages/customer/RequestOrderPage.jsx'
import './styles/app.css'

function App() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const closeNav = useCallback(() => setMobileNavOpen(false), [])
  const { route, go } = useHashRoute(closeNav)
  const { orders, quote, loading, notice, error, refresh, mutate, dismiss } = useDemoData()
  const isCustomer = route.startsWith('customer/')
  const shared = { orders, quote, loading, go, mutate, refresh }

  const renderPage = () => {
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
    <div className={isCustomer ? 'app customer-app' : 'app'}>
      {!isCustomer && <Sidebar active={route.split('/')[0]} open={mobileNavOpen} onClose={closeNav} go={go} />}
      <main className="main-area">
        {isCustomer ? <CustomerHeader /> : <Topbar route={route} onMenu={() => setMobileNavOpen((open) => !open)} />}
        <Toast error={error} notice={notice} onDismiss={dismiss} />
        {renderPage()}
      </main>
    </div>
  )
}

export default App
