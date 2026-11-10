# Informe de correcciones frontend - Fase 6

Fecha: 9 de noviembre de 2026. Alcance: impedir que Tracking ofrezca iniciar checkout para pedidos cancelados o eliminados. Prueba con Vite y datos de servidor ficticio en 127.0.0.1; sin PayPal, API real ni base de datos.

## Correccion

frontend/src/pages/customer/OrderTrackingPage.jsx detecta los estados terminales cancelled y deleted. Para esos pedidos no monta PayPalCheckout ni muestra un boton para crear una intencion; presenta una alerta que indica que el pago no esta disponible y pide contactar al taller.

## Reproduccion y verificacion

- Antes: stub devolvio TC-901, status=cancelled, total=1200, paid_amount=0 y remaining_balance=1200. Tracking mostraba "Pay remaining balance" y el boton "Start PayPal Checkout".
- Despues: la misma respuesta muestra "Checkout unavailable" y la alerta de pedido cancelado/eliminado; no aparece "Start PayPal Checkout".
- Network del navegador solo registro GET /api/quotes/101 y GET /api/orders/901; no hubo POST a payments ni GET a payments. Stub y Vite quedaron detenidos.
- Datos y token ficticios. No se inicio ni capturo un pago.

## Verificacion local

- node node_modules/eslint/bin/eslint.js src (desde frontend): exit code 0.
- Build DEMO con VITE_APP_MODE=demo, VITE_API_BASE_URL vacia y node node_modules/vite/bin/vite.js build: Vite 8.3.5, 61 modulos, exit code 0.

## Limite de seguridad

Es una barrera de interfaz, no una regla de autorizacion. CreateOrderPayment en el backend actualmente no valida el estado del pedido antes de crear el intento. Un cliente podria llamar directamente al endpoint si el backend lo permite; la API debe rechazar cancelled/deleted. Esta fase no modifico backend ni endpoint.
