# Matriz funcional frontend-backend — TallerClaro

Actualizada: 9 de noviembre de 2026. Las rutas se toman del checkout; “REAL no comprobado” significa que no se contactó el backend. Contratos HTTP, cuerpos/códigos y mapeos completos están en [Plan de integración Fase 1](PLAN_INTEGRACION_FRONTEND_BACKEND_FASE_1.md). Este archivo registra el consumidor por pantalla y la evidencia de ejecución actual.

| Pantalla/flujo | Método/endpoint esperado | Auth esperada | Consumidor actual | DEMO/local | Errores / brecha / evidencia |
|---|---|---|---|---|---|
| Request Form | POST /api/quotes; POST /api/quotes/{id}/generate; GET /api/quotes/{id} | Create publico; generate Basic taller; GET token cliente | apiClient.createQuote | mockApi fixture DEMO | REAL wire tested with local stub: create body/customer data, customer_token, first generate 503. UI received draft, showed explicit error, total unknown and no approve. Not real API or AI. |
| Quote Review | GET /api/quotes/{id}; POST .../generate; POST .../approve; POST .../reject | Customer token o workshop Basic; generate exige Basic de taller | getQuote, retryQuoteGeneration, submitMissingInfo, approveQuote, rejectQuote | mock quote en localStorage | Stub local: Draft tras 503 y retry 200 -> pending_review; missing_info visible. Sugerencias iniciales se hidratan y se limpian/cancelan al cambiar quote ID; evita arrastrar productos entre clientes. Formulario conserva texto en 503 y lo limpia al 200. Cliente no puede enviar aclaraciones sin contrato autorizado. Sin API/IA/Channel3 reales. |
| Quotes list/lookup | GET quote individual; listado no existe en backend | Customer token; lookup del taller requiere Basic | `QuotesPage` pide GET por ID con opción workshop | Solo quote activa + pedidos ejemplo | Demo lookup 1050→quote probado. REAL inbox completa pendiente; lista del UI se etiqueta lista de órdenes y no de quotes. |
| Orders | `GET /api/orders?limit&offset`; `PATCH /api/orders/{id}` | Basic taller | `apiClient.listOrdersPage/updateStatus` | Fixtures; localStorage | REAL envía limit/offset y muestra total, botones anterior/siguiente y estado de carga/error. Servidor local ficticio comprobó 45 resultados, páginas 1–20/21–40/41–45, retroceso y límites; no es backend real. REAL ofrece solo estados backend. API/DB real pendiente. |
| Order Detail | GET /api/orders/{id}, PATCH /api/orders/{id} | Basic taller; customer token si se usa via enlace cliente | OrderDetailPage llama getOrder(id); apiClient.updateStatus | mockApi por ID en DEMO | DEMO TC-1048 probado sin pagos sinteticos. REAL GET y PATCH probados con stub: total $1,200, paid $600, balance $600, payment deposit completed; transicion pending->in_progress y recarga. Backend/auth real sigue pendiente. |
| Customer Tracking | GET /api/quotes/{id}; GET /api/orders/{id} via getCustomerOrder | X-Customer-Token por recurso | useDemoData, apiClient.getQuote/getCustomerOrder/getOrder, OrderTrackingPage | Orden de muestra enlazada a quote local | Stub REAL: solo X-Customer-Token, pagos/saldo mapeados. Al cambiar quote ID, scope oculta respuesta anterior y respuestas HTTP tardias obsoletas se descartan; 403 no deja quote previo visible. Stub, no API real; ownership del servidor sin verificar. |
| Checkout | POST /api/orders/{id}/payments; GET /api/payments/{id}; POST /api/payments/{id}/capture | Customer token; captura verificada por servidor | PayPalCheckout, return page y apiClient; Tracking no monta checkout con order.status cancelled/deleted | No hay pago en DEMO | Stub cancelado: GET quote/order solamente; sin CTA ni requests de payment. No se probaron Sandbox, DB, auth real, captura ni reconciliacion. Backend todavia no valida status en CreateOrderPayment. |
| Payment Return/Cancel | GET payment; POST capture cuando estado lo requiere | Customer token | `PaymentReturnPage` | Estado local sin intento | Ruta sin intento sí se probó en baseline. Sin transacción ni proveedor real. |
| Dashboard | GET /api/orders; GET /api/accounting/summary | Basic taller | useDemoData, apiClient.getFinancialSummary, DashboardPage | Summary local DEMO; pedidos fixture | Contadores globales usan el summary y no solo los primeros 20 pedidos. REAL 33/12/8/4 y fallo 503 probados con stub local; error visible, valores no disponibles y retry; no es backend real. |
| Accounting | `GET /api/accounting/summary`, `POST /api/accounting/assistant` | Basic taller | `getFinancialSummary`, `askAccountingAssistant` | Totales/respuesta local simulados | UI ya diferencia demo/error; fake summary probado antes. API/DB/AI no probados. |
| Receipts | Ninguno implementado | A definir | Ningún endpoint de upload | Nombre de archivo local, sin bytes | UI DEMO responsive probada; REAL muestra no disponible. Contrato/storage pendiente. |
| Dictado | Web Speech API del navegador; no endpoint propio identificado | Permiso browser y posible proveedor de reconocimiento del navegador | `useSpeechInput` en textarea Request Form | Independiente de DEMO/REAL, pero requiere navegador | Mock de API probó start/stop, append y error. Incidente nativo accidental documentado; no repetir sin permiso. |

No se observó tráfico `/api/` durante la prueba DEMO. La matriz no equivale a prueba de contratos contra servidor.

### Evidencia local adicional — Fase 7

- Request -> Quote Review en DEMO reprodujo la omisión de medidas en inglés. Tras extender `extractMeasurements`, Chromium mostró `120 cm wide · 75 cm tall · 55 cm deep`; el parser también conservó las medidas españolas.
- Request, Quote Review, Tracking, Quotes, Orders, Order Detail, Receipts y Accounting no mostraron desbordamiento horizontal a 320 px. A 390 px, menú móvil -> Orders funcionó y se cerró; Request se mantuvo dentro del viewport a 768 y 1280 px.
- ESLint y build local pasan. La prueba Vitest quedó escrita, pero no fue ejecutable porque falta el binario local; sin verificación de API/DB/proveedores. Detalles y limitaciones: [Informe Fase 7](INFORME_CORRECCIONES_FRONTEND_FASE_7.md).

### Verificación de autenticación REAL local — Fase 8

- Sin `workshopCredentials`, el cliente mostró el error explícito de sesión de taller en Dashboard y no presentó fixtures como datos reales.
- El modo REAL se ejecutó con una base loopback ficticia en puerto 9. El filtro de red `/api/` no encontró solicitudes; esto confirma el guard del cliente, no autentica FastAPI.
- No hay flujo UI para establecer `workshopCredentials`; sigue pendiente decidir login/sesión, cierre y expiración. Ver [Informe Fase 8](INFORME_VERIFICACION_AUTH_FRONTEND_FASE_8.md).

### Login de taller — Fase 9

- REAL bloquea rutas hasta iniciar sesión, muestra un formulario de username/password y valida con `GET /api/orders?limit=1&offset=0`.
- Basic se conserva solo en memoria, requiere HTTPS salvo loopback, se borra al recargar, cerrar sesión o recibir 401; logout/401 oculta datos.
- Prueba positiva/negativa y expiración con stub loopback ficticio, no FastAPI. Resumen 503 se mostró como error y `—`, sin ceros. Vea [Informe de login Fase 9](INFORME_IMPLEMENTACION_LOGIN_TALLER_FASE_9.md).

### Verificacion local para publicacion — 9 de noviembre de 2026

- Backend: la suite fake-backed se ejecuto desde `Backend/.venv` con `--basetemp` dentro del workspace y sin plugin de cache: **314 passed**. No se conecto PostgreSQL.
- Frontend: ESLint directo desde `frontend/node_modules/.bin` y build Vite 8.3.5 pasaron. `pnpm run` no pudo abrir el lock del store global en el sandbox; Vitest no existe en `node_modules`, por lo que no se ejecutaron tests automatizados frontend.
- Esto es evidencia local de codigo, mocks y build; no cambia el estado de verificacion REAL de API, DB o proveedores.
