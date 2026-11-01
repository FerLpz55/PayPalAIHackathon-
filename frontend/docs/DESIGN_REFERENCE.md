# Design Reference Notes

## Source reviewed

The connected Penpot project was queried through its MCP connection. The file contains seven pages. Pages 1–4 each have a 1400 × 1000 desktop board; pages 5–7 each contain a 1280 × 820 SVG-based customer screen with a journey label. Shapes, text, screen titles, text values, dimensions, and selected style values were inspected. Penpot prototype interactions were not exposed in the inspected shape hierarchy; the frontend navigation is implemented from the screen titles and documented product journey.

## Screens represented

| Penpot page | Source screen | Frontend route |
| --- | --- | --- |
| 1 | Main dashboard and order input | `#/dashboard` |
| 2 | AI quote builder and advance invoice review | `#/quotes`, `#/customer/quote` |
| 3 | Material receipts and order tracking | `#/receipts`, `#/order/:id`, `#/customer/tracking` |
| 4 | Final payment and monthly accounting | `#/accounting` |
| 5 | Customer requests an order | `#/customer/new` |
| 6 | Customer reviews quote and deposit | `#/customer/quote` |
| 7 | Customer tracks order and payment balance | `#/customer/tracking` |

## Visual values

The code centralizes the inspected palette as CSS custom properties in `src/styles/app.css`.

| Use | Value |
| --- | --- |
| Primary navy | `#003087` |
| Action blue | `#0070E0` |
| Confirmed/received green | `#13A66B` |
| Main text | `#172B45` |
| Secondary text | `#64758B` |
| App background | `#F3F7FC` |
| Borders | `#DCE5F0` |
| Pale blue | `#EAF3FF` |
| Pale green | `#E8F8F0` |
| Deposit/status accent | `#FFBF36` |

The admin board uses a fixed left navigation, white work surfaces, thin blue-gray borders, compact Inter typography, and green payment/progress emphasis. Customer screens use a wider centered layout without the admin navigation. The frontend adapts those layouts to narrow viewports and keeps the order table scrollable when its columns need more width.

## Demo content

Names, order totals, monthly figures, and receipt states shown in Penpot are examples. The frontend labels local figures as demo data and does not represent them as verified AI estimates, PayPal transactions, or backend records.
