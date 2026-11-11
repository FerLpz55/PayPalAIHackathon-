# Informe de pruebas E2E — TallerClaro

Actualizado: 9 de noviembre de 2026. **No se ejecuto E2E frontend-FastAPI/PostgreSQL/proveedores.** Se hicieron comprobaciones locales de DEMO y un flujo REAL contra un stub HTTP ficticio en localhost; este stub valida el cableado del cliente, no el backend ni la persistencia.

## Evidencia ejecutada

| Prueba | Resultado |
|---|---|
| Pedido cancelado sin checkout | Stub devolvio status=cancelled y saldo positivo. Antes aparecia Start PayPal Checkout; despues aparece alerta y no se monto PayPalCheckout. Solo GET quote/order en Network, sin requests de pago. Stub local; backend no probado. |
| Quote Review: conservar detalles ante fallo | Antes, el guard sin sesion de taller vaciaba el campo al mostrar error. Despues, stub local devolvio 503 y el texto se conservo; respuesta 200 mas GET pending_review refresco quote y limpio el texto. Datos/Basic ficticios en loopback; sin backend/IA real. |
| Quote Review: preguntas requeridas | Stub GET /api/quotes/101 devolvio needs_information con dos textos ficticios en missing_info. Antes solo se mostraba el estado; despues la pagina muestra ambos como lista accesible. Verificado por snapshot/find en Chromium; solo stub local. |
| Quote Review: sugerencias por ID | Dos quotes ficticias: 101 devolvio un producto y 102 ninguno. Se reprodujo producto 101 retenido en 102; despues se verifico carga, limpieza al cambiar ID y descarte de busqueda retrasada de 101. Chromium sin errores; stub loopback solamente. |
| Arranque Vite local DEMO | Correcto, Vite 8.3.5, `http://127.0.0.1:5173/`, detenido al terminar. |
| Dashboard DEMO | Renderizó 8 fixtures y un aviso DEMO; sidebar incluyó Receipts DEMO. |
| Dashboard summary/error con stub local | REAL mostro conteos ficticios 33/12/8/4 de GET /api/accounting/summary. Stub 503 mostro mensaje de error, cuatro valores desconocidos, reintento y conservo la tabla de ocho pedidos; el reintento volvio a enviar GET. El 503 genero entradas de consola de recurso esperadas. Stub local, no backend real. |
| Solicitud → Quote Review | Datos ficticios → revisión; estado `Draft · not validated`, medidas 1.20 m/0.75 m y profundidad desconocida, sin `undefined`; aviso indica que no hubo backend/IA. |
| Quote create/generation failure and retry with local stub | POST /api/quotes sent customer/name/email/request JSON without auth; POST generate sent dummy Basic and got 503. GET with dummy X-Customer-Token returned draft; UI showed Draft, total unknown, visible provider error/retry and no approve button. Retry sent POST generate, got 200 and GET quote; UI showed items, $1,200 total, $600 deposit/balance, pending_review and enabled Approve. No approval/payment performed; stub only, no AI/API/DB. |
| Approve demo → Tracking | Acción explícita “Simulate demo approval” → TC-1050 sample; saldo $1,200; sin botón checkout ni transacción falsa. |
| Quote lookup | Quotes, ID 1050 → ruta `#/customer/quote?id=TC-1050` y quote correcta cargada desde el store aislado. |
| Order Detail DEMO | TC-1048: total/pagado/saldo ilustrativos, ningun payment record; no aparecen splits 50/50 ni pagos fabricados. |
| Order Detail REAL with local stub | GET /api/orders/1001 returned fictional total $1,200, paid $600, remaining $600 and one completed deposit of $600; UI rendered them. PATCH /api/orders/1001 sent {"status":"in_progress"}, returned the new status and triggered GET refresh. Dummy Basic only; not FastAPI or DB. |
| Customer Tracking with local stub | GET /api/quotes/501 and GET /api/orders/901 used X-Customer-Token: dummy-customer-token; neither request sent Basic. UI showed two completed payments totaling $1,200, zero balance and no checkout. With activeOrderQuoteId mismatched from quote ID, UI showed no order and made no GET order request. Stub-only evidence; no backend. |
| Cambio de quote y respuesta 403 | Antes, TC-101 seguia visible tras GET TC-102 -> 403. Despues, con carga limpia se oculto el snapshot anterior; alerta 403 visible y estado sin quote. Sin errores React ni warnings; el navegador registro el recurso HTTP 403 esperado. Stub local, no ownership real. |
| Cambio de token para el mismo quote | Token ficticio A cargo TC-101; token B para el mismo ID recibi? 403. Al cambiar de sesi?n en la pesta?a, el contenido A dej? de aparecer y Tracking mostr? estado vac?o/alerta. Un ?nico error de red esperado por el 403; sin warnings/errores JS. Stub local, ownership real no verificado. |
| Recibos responsive | A 390×844 CSS px: `documentElement.scrollWidth=380`, `clientWidth=380`, selector 350 px dentro de x=15…365. |
| Dictado con mock | Constructor `FakeSpeechRecognition` confirmado antes de clics. `start`, idioma `en-US`, `interimResults=false`, `stop`, append al texto previo y mensaje `not-allowed` pasaron sin audio. |
| Paginación REAL con stub local | Servidor HTTP ficticio en `127.0.0.1:8001` devolvió 45 órdenes y registró Basic de prueba local. UI mostró 1–20, 21–40, 41–45; hizo `GET /api/orders?limit=20&offset=0`, luego offset 20/40 y regreso a 20; deshabilitó Next al llegar a la última página. Cero errores de consola. No contactó FastAPI/PostgreSQL ni servicio externo. |
| Network/consola | Sin llamadas `/api/` en la sesión DEMO. No se reportó fallo de consola en las rutas revisadas. |
| ESLint | `node node_modules\eslint\bin\eslint.js src` → exit 0. |
| Build | `VITE_APP_MODE=demo`, `VITE_API_BASE_URL=''`; `node node_modules\vite\bin\vite.js build` → 61 módulos, éxito. |
| Aserciones auxiliares | Once assertions Node para money/medidas/unknowns/saldo → passed. Tras la corrección por modo, dos assertions directas verificaron que REAL expone solo estados de pedidos del backend y DEMO conserva sus estados fixture. |
| Vitest | No ejecutado: `frontend/node_modules/vitest` no existe; pnpm no tiene acceso al lock de su store. No se instalaron deps. |

## Incidente de dictado nativo

En un intento previo de inyectar la implementación fake, el objeto se perdió al navegar. El clic ejecutó Web Speech nativo en una pestaña/contexto aislado; Chromium informó permiso concedido y recibió una transcripción en inglés agregada al texto escrito. No se envió la solicitud ni se creó quote. No puedo confirmar si el audio se transmitió fuera del browser; debe tratarse como posible transmisión accidental. Se cerró la pestaña y no hubo más activaciones nativas. Las pruebas posteriores sustituyeron y verificaron el constructor fake antes de cada clic.

## No probado

- Servicio/backend FastAPI, CORS desplegado, DB/persistencia, migraciones, auth/ownership de recursos.
- Quote generation con proveedor IA, Channel3, PayPal Sandbox, return/cancel/capture, recuperación/duplicados.
- Navegadores móviles/physicos, Voice API nativa bajo autorización, Safari/Firefox, AT/lector de pantalla.
- Vitest automatizado y suite backend en esta fase. El reporte del usuario de backend `314 passed` es contexto previo, no ejecución actual; ningún archivo backend fue tocado.

No se usó PostgreSQL ni credenciales. No se cerraron issues. Siguiente prueba E2E requiere infraestructura de prueba identificada y autorización para servicios Sandbox; ver `PENDIENTES_INFRAESTRUCTURA_Y_CREDENCIALES.md`.

## Verificaciones locales añadidas en Fase 7

- Se reprodujo en DEMO que `120 cm wide` se mostraba sin medidas en Quote Review; después de la corrección, el navegador mostró dimensiones completas en inglés y mantuvo los datos al recargar. Una importación del adaptador confirmó también el formato español. No se utilizó IA ni backend.
- Reflow sin overflow horizontal: ocho rutas a 320 px, navegación móvil a 390 px y Request a 768/1280 px. Solo Chromium local.
- ESLint y build terminan con código 0. El test automatizado Vitest no corrió porque su binario no existe localmente; no se instalaron paquetes. Ver [Informe Fase 7](INFORME_CORRECCIONES_FRONTEND_FASE_7.md).

### Guardia de autenticación REAL — Fase 8

Modo REAL con `VITE_API_BASE_URL=http://127.0.0.1:9`, sin servicio ni credenciales: el guard detuvo la llamada de taller antes de `fetch`, Dashboard mostró alertas y no mostró pedidos DEMO. Network no registró `/api/`. El test confirma comportamiento fail-closed del cliente, no autenticación real. No hubo requests externos. Ver [Informe Fase 8](INFORME_VERIFICACION_AUTH_FRONTEND_FASE_8.md).

### Login REAL con stub — Fase 9

Validación local aislada: credencial ficticia incorrecta -> 401 visible y sigue fuera; credencial ficticia correcta -> GET protegido 200 y Basic coincidió en stub; 401 posterior -> logout automático, datos ocultos; logout manual; reload pide autenticación de nuevo. No hay credencial en Web Storage. Sólo stub HTTP loopback; no FastAPI, DB o servicio externo. Resumen 503 fue visible y no se convirtió en ceros. Evidencia: [Informe Fase 9](INFORME_IMPLEMENTACION_LOGIN_TALLER_FASE_9.md).

## Verificacion local de publicacion — 9 de noviembre de 2026

- Desde `Backend/`, con `UV_NO_SYNC=1` para impedir sincronización/instalación: `uv run pytest tests/unit/test_repository_contracts.py -v` -> **15 passed in 0.38s**.
- Después: `uv run pytest -v` -> **314 passed in 9.05s**. Ambos son tests locales con fakes/SQL scripted; no PostgreSQL ni proveedores.
- Frontend ESLint directo -> exit 0. Build Vite 8.3.5 directo -> exit 0 (62 modules transformed). Vitest no pudo ejecutarse: `frontend/node_modules/.bin/vitest.cmd` no existe. Los comandos `pnpm run` encontraron permiso denegado al abrir el lock del store global. No se instalaron dependencias.
- No se repitio el navegador/stub; se conserva la evidencia de las fases anteriores. Esta comprobacion no convierte los flujos stub en pruebas contra el backend real.
