import Navbar from '../widgets/Navbar/Navbar.jsx'
import { RequestForm, HowItWorks } from '../features/quote-request'
import './RequestOrderPage.css'

function RequestOrderPage() {
  function handleQuoteCreated(quote) {
    console.log('Quote created', quote)
  }

  return (
    <div className="request-page">
      <Navbar workshopName="Madera Norte" workshopType="Carpentry studio" />
      <main className="request-page__body">
        <header className="request-page__heading">
          <span>New order</span>
          <h1>What would you like us to make?</h1>
          <p>
            Describe your piece in your own words. Our AI turns it into a detailed quote for the
            workshop to approve.
          </p>
        </header>
        <div className="request-page__columns">
          <RequestForm onQuoteCreated={handleQuoteCreated} />
          <HowItWorks />
        </div>
      </main>
    </div>
  )
}

export default RequestOrderPage
