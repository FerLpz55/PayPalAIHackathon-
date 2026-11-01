import PageHeading from '../../components/ui/PageHeading.jsx'
import HowItWorks from '../../components/customer/HowItWorks.jsx'
import RequestForm from '../../components/customer/RequestForm.jsx'

function RequestOrderPage({ go, refresh }) {
  const handleQuoteCreated = async () => {
    await refresh()
    go('customer/quote')
  }

  return (
    <div className="customer-page">
      <PageHeading title="What would you like us to make?" description="Describe your piece in your own words. Get a clear estimate to review with the workshop." />
      <div className="customer-request-grid">
        <RequestForm onQuoteCreated={handleQuoteCreated} />
        <HowItWorks />
      </div>
    </div>
  )
}

export default RequestOrderPage
