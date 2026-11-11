# Plan de integración frontend-backend — Fase 1

Fecha: 9 de noviembre de 2026. Revisión estática focalizada del código actual de `PayPalAIHackathon-`, tomando `AUDITORIA_TECNICA_PAYPAL_AI_HACKATHON.md` como línea base.

## 1. Resumen ejecutivo

El código actual tiene más integración explícita que un modo de demo genérico: el frontend distingue DEMO de REAL, tiene un cliente HTTP, adapta respuestas snake_case y llama rutas para cotizaciones, órdenes, pagos y contabilidad. Eso confirma contratos en fuente, no disponibilidad del backend, de PostgreSQL ni de proveedores.

Siguen bloqueando una integración segura el Basic Auth fijo del frontend, la falta de un flujo real de acceso de taller, el token de cliente restringido al almacenamiento de una pestaña/sesión de navegador y varias pantallas que no usan endpoints ya existentes. La UI todavía trata estados de pedido como `quote_sent` y `ready_to_finish`, que el backend y su esquema actual no aceptan. El error de generación de cotización se absorbe y puede dejar una cotización `draft` con apariencia de propuesta preparada.

La revisión no ejecutó pruebas, frontend, servidor, migraciones, comandos de configuración ni llamadas de red. El usuario informa que Python 3.11.10, `.venv`, dependencias backend, lock y pnpm 12.16.1 ya están preparados. La carpeta `Backend/.venv` está presente; no volví a sincronizar ni a comprobar versiones. No leí valores de `.env`. No se conectó a base de datos o servicio alguno. La persistencia real sigue sin verificar.

## 2. Estado actualizado de hallazgos anteriores

| Hallazgo | Estado | Evidencia del código actual y precisión |
|---|---|---|
| Basic Auth fijo en frontend | **CONFIRMADO** | `frontend/src/services/http.js`: para toda ruta de taller, si no hay credencial de sesión, crea `Basic` desde `btoa('credencial Basic de demostracion incrustada')`. No encontré flujo UI/API que establezca `workshopCredentials`. Backend valida usuario y hash bcrypt (`Backend/src/tallerclaro/infrastructure/security/workshop_auth.py`). En una instalación configurada correctamente, el fallback no autentica; en cualquier caso, la credencial está incorporada al bundle. |
| Error de generación de cotizaciones oculto | **CONFIRMADO** | `frontend/src/services/apiClient.js`, `createQuote()`: captura cualquier error del POST `/generate` sin informar al usuario y luego solicita GET de la cotización. El endpoint devuelve `draft` si no hubo generación (`Backend/src/tallerclaro/application/use_cases/quotes.py`). La adaptación puede representar total ausente como cero (`frontend/src/services/adapters.js`). |
| Customer token almacenado únicamente en `sessionStorage` | **CONFIRMADO** | El token crudo se guarda en `tallerclaro.session.v1` mediante `frontend/src/services/sessionStore.js`; no aparece en `localStorage`. La API guarda en DB solo su hash y expone el token en la respuesta inicial (`Backend/src/tallerclaro/application/use_cases/quotes.py`, `presentation/http/mappers.py`). No hay flujo de enlace/email para reentrega o recuperación. Sobrevive a recargas en la pestaña, pero no ofrece recuperación desde otra sesión/dispositivo. |
| Recuperación de pagos inciertos ausente | **PARCIALMENTE CORREGIDO** | `apiClient`/`PayPalCheckout`/`PaymentReturnPage` ya consultan GET `/api/payments/{id}`, verifican identidad/estado y permiten reintentar captura de un intento conocido. La referencia sigue en `sessionStorage`; si se pierde la respuesta del POST de creación, queda una marca `unresolved` sin `paymentId`, bloquea un nuevo intento y pide reconciliación manual. No hay consulta backend por orden que recupere el intento desconocido, ni mecanismo de recuperación tras perder la sesión. |
| Quotes list y lookup incompletos | **CONFIRMADO** | No existe GET de listado de cotizaciones. `QuotesPage` filtra pedidos de GET `/api/orders` con estados `pending`/`quote_sent`; no es un listado de quotes. El lookup obtiene una cotización individual, pero solo pasa token del cliente, no Basic del taller. La navegación lleva el ID en query string; `useHashRoute` elimina la query y `useDemoData` vuelve a llamar `getQuote()` con el ID activo de `sessionStorage`, sin hidratar desde el ID solicitado. |
| Order Detail sin consulta real por ID | **CONFIRMADO** para la pantalla; **PARCIALMENTE CORREGIDO** en la capa de servicio | Existe `apiClient.getOrder(id)` y el backend implementa GET `/api/orders/{id}` con detalle, pero `OrderDetailPage` busca en el arreglo `orders` ya cargado y no invoca el método. Si el pedido no está en la página/lista cargada, lo muestra como inexistente. |
| Pagos mostrados con valores ficticios | **CONFIRMADO** en Order Detail | `OrderDetailPage` representa siempre anticipo y saldo como “50%”, usando `order.deposit` y `order.balance` derivados, y presenta estados desde estado general del pedido; no renderiza `order.payments`. El endpoint de detalle sí devuelve pagos verificados, pero esa pantalla no lo consume. `OrderTrackingPage` sí muestra `payments` cuando recibe el detalle del cliente. |
| Errores contables convertidos en ceros | **CONFIRMADO** | `AccountingPage` usa `.catch(() => {})`, conserva `summary = null` y dibuja métricas con `?? 0`. En modo REAL, un fallo se presenta como cantidades cero, no como error. |
| Ausencia de endpoints de recibos y gastos | **CONFIRMADO** | Los routers disponibles no incluyen receipts/expenses y el esquema HTTP de accounting no los define. `ReceiptsPage` solo existe en DEMO y `mockApi.addReceipt` conserva el nombre/metadata local, no los bytes. El backend no contiene modelo/ruta para gastos. |
| Problemas de CORS | **CONFIRMADO como configuración predeterminada riesgosa** | `bootstrap/settings.py` da `cors_origins = ['*']` por defecto; `main.py` habilita `allow_credentials=True`, métodos y headers `*`. Se admite configurar lista explícita, pero no se inspeccionaron valores de entorno ni respuesta en vivo. No afirmo el comportamiento efectivo de un despliegue concreto. |
| Estados de órdenes y cotizaciones incompatibles | **CONFIRMADO** | Backend: cotizaciones `draft`, `needs_information`, `pending_review`, `approved`, `rejected`; pedidos `pending`, `paid`, `in_progress`, `delivered`, `cancelled`, `deleted`. La UI conserva `quote_sent` y `ready_to_finish` como estados de pedido (`frontend/src/utils/constants.js`) y usa pedidos para llenar Quotes. El esquema SQL rechaza estados de pedido fuera de su CHECK; una transición inválida de aplicación acaba en conflicto. |

### Cambios respecto a la auditoría anterior

- La consulta de pedido por ID y el contrato de detalle ya existen en el cliente y backend. La brecha se limita ahora a que `OrderDetailPage` no los usa; no es correcto afirmar que no exista ningún GET por ID en código.
- La recuperación de pago tiene pasos de lectura/verificación/reintento para un `paymentId` guardado. La recuperación de un resultado desconocido, de una sesión perdida o de un pago sin ID sigue sin solución automática.
- El modo real no cambia a datos de demo automáticamente: sin URL configurada se bloquea con estado de configuración; DEMO requiere `VITE_APP_MODE=demo`. El mock usa `localStorage` solo para datos demo (`mockApi.js`).
- El estado informado de preparación local cambió desde el diagnóstico anterior: `.venv` está presente y el usuario informa dependencias y lock aprobados y 314 pruebas backend aprobadas. No repetí esos comandos.

## 3. Matriz de contratos HTTP

Los contratos se deducen de routers, esquemas, dependencias, mappers y llamadas frontend. JSON usa snake_case. Todos los códigos de error son los definidos por validación/auth/manejadores actuales cuando la condición aplica; no son resultados observados en ejecución. `RequestValidationError` devuelve 422; errores de dominio mapean 401, 403, 404, 409, 422, 502 o 503 según código.

| Endpoint actual | Auth y request | Respuesta y códigos visibles en fuente | Llamada/diferencia frontend |
|---|---|---|---|
| `POST /api/quotes` | Pública. `{customer:{name,email,phone?}, carpenter_id, request}`. Email validado; campos extra prohibidos. | **201** `QuoteResponse`: id, customer_id, carpenter_id, request, description, items, currency, total, deposit_amount, balance_amount, status, customer_token, assumptions, missing_info, suggested_products, timestamps. **404** carpintero no encontrado; **422** validación. | Coincide con body base. Guarda el token en sesión y luego intenta generar. Dependencia de precio inicial se invoca también durante creación. |
| `POST /api/quotes/{id}/generate` | Basic taller. Body opcional `{additional_info?}`. | **200** `QuoteGenerateResponse`: id, status, description, items, total, assumptions, missing_info, suggested_products. **401/403**, **404**, **409**, **422** (respuesta IA inválida), **502/503** según proveedor. No devuelve depósito/saldo; frontend vuelve a leer la quote. | Usa Basic fijo en `http.js`; creation call omite body, reintento/missing info envía `additional_info`. El error inicial se oculta. |
| `GET /api/quotes/{id}` | Token cliente (`X-Customer-Token`; backend también acepta Bearer) o Basic taller. Query opcional `q`. | **200** `QuoteResponse` sin emitir token nuevo. **401/403/404**, **422** para ID. | Solo adjunta token de sesión si lo tiene; no solicita Basic al lookup de taller. `q` se concatena correctamente, pero la pantalla de catálogo silencia error y la navegación de lookup no rehidrata quote por query ID. |
| `POST /api/quotes/{id}/approve` | Token cliente o Basic taller. Sin body. | **200** `OrderResponse` (pedido recién creado o existente). **401/403/404/409/422**. | POST coincide; luego guarda ID de pedido y GET de quote. La autorización depende de token o credencial funcional; el fallback Basic no resuelve acceso taller. |
| `POST /api/quotes/{id}/reject` | Token cliente o Basic taller. Sin body. | **200** `QuoteResponse`. **401/403/404/409** si estado no editable. | Coincide en método/cuerpo; vuelve el quote adaptado. |
| `GET /api/orders` | Basic taller. `limit` por defecto 20, rango 1–100; `offset` por defecto 0, no negativo. | **200** `{orders:[OrderResponse], total, limit, offset}`. **401**; **422** query inválida. OrderResponse no trae historial ni paid amount. | Envía Basic; entiende wrapper. No pasa `limit`/`offset`; lista solo primera página (20 por defecto), sin controles de paginación UI. |
| `GET /api/orders/{id}` | Token cliente o Basic taller. Path integer. | **200** `OrderDetailResponse`: OrderResponse + `payments` (id/type/amount/status/paypal_order_id), `paid_amount`, `remaining_balance`, customer y proyecto. **401/403/404/422**. | `apiClient.getOrder()` existe y selecciona token/Basic, pero `OrderDetailPage` no lo llama. El detalle de pagos y montos queda sin usar. |
| `PATCH /api/orders/{id}` | Basic taller. `{status?: string, estimated_delivery_date?: YYYY-MM-DD}`; extra prohibido. | **200** `OrderResponse`. **401/403/404/409** transición/pago incompleto; **422** cuerpo/date. | Envía `{status}` y adapta respuesta. La UI ofrece estados no aceptados por el backend, además de `paid` que el backend gestiona por cobro. |
| `POST /api/orders/{id}/payments` | Token cliente. `{type: "deposit" | "balance"}` (schema documenta valores, use case valida). | **200** `PaymentIntentResponse`: `payment_id`, `paypal_order_id`, `amount`, `currency`, `approval_url`. **401/403/404/409/422/502/503**. Efectúa creación con provider externo si configurado. | Coincide con tipo y valida la URL de PayPal. Persiste recuperación solo en `sessionStorage`; si la conexión cae antes de recibir IDs, no hay lookup backend por orden. |
| `GET /api/payments/{id}` | Token cliente de la quote asociada. | **200** `PaymentResponse`: id, order_id, type, amount, currency, status, paypal IDs, created_at, paid_at. **401/403/404/422**. | `apiClient.getPayment()` lee el recurso. Puede verificar una tentativa cuyo ID esté conservado por el browser. |
| `POST /api/payments/{id}/capture` | Token cliente. Sin body. | **200** `CapturePaymentResponse`: payment_id, status, PayPal order/capture IDs, amount, currency, paid_at. **401/403/404/409/422/502/503**. La captura implica llamada al provider externo. | Envía POST, exige `completed`, luego las pantallas pueden volver a GET. No ejecutado. |
| `GET /api/accounting/summary` | Basic taller. Sin parámetros. | **200** `FinancialSummaryResponse`: currency, conteos y montos agregados. **401/403** y errores de dominio/DB según condición. | Llama correctamente; en fallo la pantalla no muestra error y sustituye datos ausentes por ceros. |
| `POST /api/accounting/assistant` | Basic taller. `{question}` de 3–500 caracteres (esquema actual no declara `extra='forbid'`). | **200** `{question, answer, summary}`. **401/403/422/502/503** si aplica servicio IA. | Coincide en JSON y ruta; no persiste conversación. La ruta Basic también usa fallback fijo. |

### Rutas adicionales encontradas

- `GET /api/health`: pública, **200** `{status:"ok"}`. La función no consulta DB. Sin embargo, el lifespan normal intenta conectar DB antes de servir tráfico; no es una prueba de disponibilidad del pool ni de persistencia.
- `DELETE /api/orders/{id}`: Basic taller, respuesta `OrderResponse`, borrado lógico a `deleted`; `include_in_schema=False` (no sale en OpenAPI). Frontend actual usa `PATCH {status:"deleted"}`, que sí coincide con el uso de UpdateOrder.
- No encontré rutas de lista de cotizaciones, clientes, recibos, gastos, correo, reemisión de token o recuperación de pagos por pedido.

## 4. Preparación del frontend

### Modo y URL

- `frontend/src/services/http.js` lee `VITE_APP_MODE` y `VITE_API_BASE_URL` en build. DEMO está habilitado solo cuando `VITE_APP_MODE` equivale a `demo`; entonces `apiClient` enruta las funciones compatibles al `mockApi`.
- REAL requiere URL base no vacía y que DEMO no esté activo. Si falta, `App` presenta modo no configurado y no muestra datos demo. Una variable `VITE_APP_MODE` distinta a `demo` no activa mocks.
- El transporte quita barras finales de `VITE_API_BASE_URL`; cada llamada usa rutas absolutas con `/api/...`, y concatena `${API_BASE_URL}${cleanPath}`. Configurar el **origen del backend sin `/api`**, por ejemplo `https://host-backend` o `http://localhost:8000`. Si se configura `.../api`, el frontend generará `.../api/api/...`.
- No inspeccioné `.env` ni valores cargados en un deployment. No puedo confirmar qué URL, modo, credenciales o allowlist están vigentes.

### Cliente, datos y auth

- `http.js` centraliza `fetch`, `Content-Type: application/json`, extracción de mensajes y errores con `status`. No añade timeout/reintento general.
- Se envía `X-Customer-Token` desde opciones/sesión; el backend también permite `Authorization: Bearer`, pero el cliente no utiliza ese mecanismo. Rutas `isWorkshopRoute` agregan Basic y usan el fallback fijo ya descrito. No hay login UI visible.
- `sessionStore.js` limita quote ID, token y referencias de pago al `sessionStorage`. `mockApi.js` guarda solo fixtures DEMO bajo `localStorage` y simula latencia de 220 ms.
- `adapters.js` adapta claves snake_case, nombres, IDs y montos a camelCase. Fallbacks como quote total ausente→0, medidas por defecto y depósito calculado 50% pueden hacer plausible una respuesta incompleta; preservar un campo de datos faltantes separado evita confundirlo con una cifra válida.
- `useHashRoute()` quita query string antes de elegir página. El componente de quote recibe estado desde `useDemoData()` y no procesa el ID de `#/customer/quote?id=...`; el lookup GET no persiste el quote recién encontrado.

## 5. Preparación del backend y persistencia

- **Instalado:** usuario informa Python 3.11.10 y `uv sync --locked --extra dev`; `.venv` se encuentra en el árbol y `pyproject.toml` requiere Python >=3.11. No repetí instalación, `uv lock --check` ni pruebas.
- **Contradicción documental relevante:** el `AGENTS.md` raíz todavía indica Python 3.14, mientras `Backend/pyproject.toml` declara `>=3.11` y el entorno informado es 3.11.10. Conviene corregir esa instrucción documental en una tarea autorizada para no dar recomendaciones de runtime incompatibles.
- **Arranque sin DB:** el objeto FastAPI se compone en `create_app()`, pero el lifespan normal llama `Database.connect()` al arrancar Uvicorn. Por tanto, no se puede considerar una instancia normal arrancable/servida sin PostgreSQL. `/api/health` en sí no usa DB, pero el arranque de producción sí espera el pool.
- **Arranque con DB:** la ruta de arranque está implementada si existe DSN accesible, credenciales válidas y hash bcrypt válido. `ensure_workshop_auth_configured()` aborta si no hay hash utilizable; `Database.connect()` abre pool y espera conexión. No se comprobó con una base.
- **Persistencia comprobada realmente:** **no**. La revisión fue estática y no ejecutó SQL ni conectó PostgreSQL/Supabase. Las 314 pruebas informadas prueban el código según reporte del usuario; no equivalen a persistencia real.
- Settings viven en `Backend/src/tallerclaro/bootstrap/settings.py`, con `.env` y entorno; `DATABASE_URL`/`TALLERCLARO_DATABASE_URL`, hash Basic, secreto/TTL token, CORS, AI, búsqueda de precios y PayPal. Los valores por defecto DB/token son de desarrollo (`change-me`); el hash Basic debe configurarse para permitir startup.
- CORS se monta en `main.py`. Debe definirse una lista exacta de orígenes del frontend en el entorno que vaya a usarse; actualmente el default es comodín con credenciales.
- Dependencias HTTP resuelven una fábrica de UoW por request (`app.state.uow_factory`), repositorios PostgreSQL y adaptadores IA, precio y PayPal. Las rutas y casos de uso separan llamadas externas de transacciones en los flujos revisados. Esto describe diseño de fuente, no disponibilidad de servicios.
- Las migraciones presentes son `001_add_customer_link_tokens.sql`, `002_add_quote_clarification_fields.sql`, `003_reserve_payment_capture.sql`, `004_add_cancelled_order_status.sql`. No encontré ejecución automática de migraciones en lifespan; `schema.sql` es estado completo para DB nueva. No se comprobó qué versión tiene ninguna base.

## 6. Problemas confirmados y diferencias frontend-backend

1. **No hay autenticación de taller utilizable por el frontend actual.** El cliente envía Basic fijo; backend compara usuario y password contra configuración/hash bcrypt y rechaza hash inválido al arrancar. Antes de un modo real debe existir un origen autenticado y no incrustado para la credencial o sesión.
2. **Fallo de generación puede mostrarse como cotización lista.** El endpoint inicial de quote crea draft y token; la generación necesita Workshop Basic y AI. El frontend absorbe fallo, recupera el draft y sus adaptadores cubren totales ausentes con cero.
3. **Quote lookup/listado no coincide con acceso ni ruta.** Falta lista; la UI adapta órdenes a quotes. El cliente no añade Basic al lookup por taller y no carga el ID de query en la pantalla.
4. **Estados de pedido no comparten un vocabulario canónico.** `quote_sent` y `ready_to_finish` son UI, no valores permitidos en DB/backend actual; las cotizaciones tienen estados independientes. Acordar ciclo de quote vs ciclo de order antes de cambiar UI o API.
5. **Detalle del taller lee una lista, no detalle.** Existe endpoint con pagos y saldo, pero la pantalla no lo invoca y dibuja pago 50/50 aproximado.
6. **Errores de summary se parecen a información financiera real.** Se absorbe el fallo y se renderizan ceros.
7. **Pago incierto solo se reconcilia parcialmente.** La recuperación de IDs conocidos funciona conceptualmente; una tentativa cuyo ID no llegó al cliente no se puede buscar por order_id mediante API actual. Estado temporal en sesión limita recuperación.
8. **CORS default demasiado amplio para un despliegue autenticado.** Aun si se pueden configurar orígenes, no hay confirmación de allowlist efectiva.
9. **Sin recibos/gastos reales.** La página y copy de demo describen muestra local. Aún no hay contrato, permisos, modelo, almacenamiento ni reglas de revisión.
10. **Contrato financiero incompleto en contabilidad.** Summary agrega contratos y pagos, no gastos/beneficio. La UI menciona “spending/expenses” en otras zonas demo; no se debe tratar como ledger o utilidad.

## 7. Bloqueos actuales

- Decisión de identidad de taller: quién autentica, cómo obtiene la UI credencial/sesión, expiración, cierre de sesión y despliegue detrás de HTTPS. No existe login endpoint en los routers.
- Entrega de token cliente: link seguro, expiración, reemisión/revocación, canal de envío y cómo abrir una quote desde otro dispositivo. El backend solo retorna el token crudo al crear.
- Origen frontend y backend de destino aún no verificados; allowlist CORS real no inspeccionada.
- DB PostgreSQL local/de pruebas descartable, credenciales/rol, estado del schema/migraciones y fixture limpio aún requieren provisión externa o aprobación operativa. No usar una DB no identificada.
- AI, Channel3 y PayPal Sandbox requieren credenciales y endpoints configurados para validar integraciones reales; aquí no se consultaron.
- Decisión funcional para recibos/gastos y para estados de pedido: almacenamiento binario, límites, acceso, retención, revisión y definición contable fuera de contrato actual.

## 8. Trabajo realizable ahora sin credenciales externas

1. Acordar y fijar el contrato OpenAPI como fuente común: naming, auth por endpoint, status codes, paginación y errores; añadir lista/lookup formal de quotes al contrato si la UI los necesita.
2. Corregir seguridad frontend: eliminar credencial Basic de bundle; implementar cliente de autenticación de taller después de acordar patrón; hacer fallos 401 visibles y no reintentar con demo.
3. Hacer fallar con mensaje claro la creación si `/generate` falla o si la respuesta sigue en `draft`/sin total. Distinguir cotización recibida de propuesta valorizada.
4. Reparar navegación por ID/query y definir `GET quote` para taller autenticado; impedir que el token de una quote anterior se use como contexto accidental para otra.
5. Unificar constantes de estado, transiciones y etiquetas con enums/respuestas backend; eliminar `quote_sent`/`ready_to_finish` del contrato activo o implementarlos explícitamente en todos los niveles.
6. Conectar Order Detail a GET de detalle, representar pagos devueltos por API, separar lista y detalles y usar total paginado.
7. Cambiar recuperación de pago para tratar explícitamente intento no identificado, persistencia de recuperación y conciliación; no habilitar segundo intento por timeout ambiguo.
8. Renderizar summary como error/loading/empty en vez de ceros falsos; distinguir “cobrado”, “pendiente de cobro”, gasto y utilidad.
9. Definir especificación de recibos/gastos antes de construir: entidades, permiso, storage, límites MIME/tamaño, borrado/retención, revisión y total contable.
10. Agregar/adaptar tests unitarios locales para los contratos nuevos y errores. Estos no necesitan proveedor real; se deben ejecutar solo en una fase posterior autorizada.

## 9. Trabajo que requiere infraestructura

### B. PostgreSQL local o base descartable

Después de elegir explícitamente una base aislada y confirmar que puede destruirse: validar `schema.sql` en instalación vacía; aplicar migraciones solo al fixture de upgrade; levantar API con DB de prueba; verificar create/get/generate fake/approve/order/payment persistido, estados, soft delete, conteo/paginación, y rollbacks. Confirmar restricciones de rol y columnas requeridas por repositorios (`captura_en_curso`, tokens, quotes). No usar producción o un DSN sin identificar.

### C. Credenciales/cuentas externas

- Configurar hash/usuario del taller, secreto token robusto y orígenes exactos; luego inspeccionar startup y preflight browser contra el host elegido.
- AI: confirmar proveedor/modelo, timeout, esquema de propuesta, campos faltantes y manejo de cuota/errores; verificar coste únicamente en staging.
- Channel3: validar contrato/respuesta/coste/timeout y texto de UI “live prices”; decidir degradación visible.
- PayPal Sandbox: client ID/secret backend, URLs HTTPS de retorno/cancelación y cuentas sandbox. Confirmar create/approve/capture/cancel/timeout/duplicados y comparación de estado, moneda, amount e IDs. No promover a Live en esta fase.
- Email/storage externo solo si se aprueba canal de acceso/entrega de enlace o almacenamiento de recibos.

## 10. Orden recomendado de implementación por etapas

| Etapa | Dominio y dependencia | Entregable | Criterio de aceptación |
|---|---|---|---|
| 0. Congelar contrato | Sin credenciales; antes de cambiar clientes | Matriz versionada para recursos, auth, roles, errores, estados, paginación e idempotencia | Cada ruta tiene un consumidor/owner; cliente y server no interpretan estados distintos; OpenAPI refleja métodos públicos. |
| 1. Seguridad y autenticación | Sin servicios externos, pero requiere decisión de identidad; precede a todo REAL | Retirar Basic embebido, configurar CORS allowlist, endurecer secretos, definir login/sesión de taller y acceso recuperable de cliente | Ninguna credencial está en bundle; auth negativa/positiva por rol y ownership; CORS solo permite orígenes acordados; token se puede recuperar/revocar según política aprobada. |
| 2. Cotizaciones | Depende de Etapa 1; IA opcional para pruebas de contrato | Manejo explícito de draft/error, quote list/lookup/navegación, estados quote, precios sugeridos y reintentos idempotentes | Fallo de IA no muestra quote “lista”; quote se abre por ID/link; la lista contiene quotes reales; total ausente se muestra como pendiente/error, nunca $0 inventado. |
| 3. Clientes | Depende de auth/token + DB descartable para persistencia | Continuidad de customer y enlace de quote | Cliente puede abrir quote desde sesión nueva conforme al método aprobado; token expirado/revocado produce error claro sin filtrar recursos. |
| 4. Órdenes | Depende de estados acordados y Etapa 2; DB para integración | Paginar pedidos; detalle por ID; transiciones e historial de pago API | List responde total y cada página; UI navega pedidos fuera de primera página; detail usa GET por ID y muestra paid/remaining/payments del backend. Estados PATCH son solo los permitidos. |
| 5. Pagos | Depende de Etapas 1 y 4, DB descartable; Sandbox externo para captura real | Crear intención, retorno y conciliación idempotente | Un timeout no causa duplicado; se recupera pago por servidor aun si browser perdió respuesta/sesión; éxito exige captura completada verificada por importe/moneda/IDs; cancelación no marca pago. |
| 6. Contabilidad | Depende de pagos/órdenes persistidos | Summary + AI assistant con errores visibles; decisión separada de gastos | Summary muestra origen temporal, moneda y error; conteos/montos concilian con filas y capturas; no se muestra beneficio sin gastos reales. |
| 7. Recibos y gastos | Depende de modelo/permisos/storage aprobado y DB; proveedor de storage si externo | Contrato y flujo de carga/revisión | Metadatos/bytes están protegidos por recurso, tipos/tamaño validados, auditoría/retención aprobadas; gasto solo suma tras validación explícita. |
| 8. E2E y preparación demo | Depende de API+DB staging, configuración segura, PayPal Sandbox y AI según alcance | Flujos completos desde solicitud hasta tracking y resumen | Request → quote → approval → pedido → pago Sandbox → captura verificada → pago mostrado → contabilidad; cobertura de rechazo, expiración, retry, red caída y usuario sin permiso. No usar credenciales Live. |

## 11. Criterios de aceptación transversales

- No hay secretos Basic, token, PayPal o AI en assets compilados; URLs de producción son HTTPS y CORS es lista explícita.
- Contratos de `frontend/src/services/apiClient.js` coinciden con routers/esquemas y OpenAPI (código HTTP, shape, required/nullable, parámetros y auth).
- Los tests locales cubren errores 401/403/404/409/422/502/503, cargas snake_case, expiración de token, estados y paginación.
- Datos demo llevan indicación visible y nunca aparecen como respuesta real ante error de conexión.
- La app distingue cargando, vacío, no configurado y fallo; números financieros ausentes no se convierten en ceros.
- DB de pruebas es efímera/recreable y el backend no ejecuta migraciones implícitamente en startup.
- Ninguna captura se presenta como completada sin confirmación backend verificada; reintentos preservan una sola intención por operación idempotente.

## 12. Comandos de verificación propuestos (no ejecutados)

Estos comandos son propuestas para una fase posterior; **no se ejecutaron en esta inspección**.

### Validación local sin servicios externos

```powershell
uv run --project Backend pytest -v
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
```

### Validación con una PostgreSQL explícitamente descartable

Solo después de identificar un DSN de prueba temporal; las operaciones SQL mutan la base seleccionada:

```bash
psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/schema.sql
psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/tests/schema_test.sql
```

Aplicar 001–004 como prueba de upgrade únicamente sobre una base descartable con estado previo reproducible; no mezclar `schema.sql` y migrations sobre una DB desconocida.

### Servicios externos / E2E

No ejecutar hasta que se aprueben URLs/credenciales Sandbox/staging y alcance:

```text
Iniciar API contra PostgreSQL staging y comprobar /api/health más una lectura controlada.
Ejecutar request → quote → approve → PayPal Sandbox → capture → order tracking.
Repetir con timeout, retorno cancelado, doble submit, sesión perdida y pago incierto.
```

`GET /api/health` por sí solo es liveness HTTP; no es una verificación de DB.

## Archivos de evidencia principales

- Frontend: `frontend/src/services/http.js`, `apiClient.js`, `adapters.js`, `sessionStore.js`, `mockApi.js`, `App.jsx`, `hooks/useDemoData.js`, `hooks/useHashRoute.js`, `pages/QuotesPage.jsx`, `pages/OrderDetailPage.jsx`, `pages/AccountingPage.jsx`, `pages/ReceiptsPage.jsx`, `pages/customer/QuoteReviewPage.jsx`, `components/customer/PayPalCheckout.jsx`, `pages/customer/PaymentReturnPage.jsx`, `utils/constants.js`.
- Backend: `Backend/src/tallerclaro/main.py`, `bootstrap/settings.py`, `presentation/http/dependencies.py`, `exception_handlers.py`, `mappers.py`, `routers/{quotes,orders,payments,accounting,health}.py`, `schemas/{quotes,orders,payments,accounting}.py`, `application/use_cases/{quotes,orders,payments}.py`, `infrastructure/{db,security}`.
- DB/contratos: `database/schema.sql`, `database/migrations/001–004`, `Backend/pyproject.toml`.
- Contexto previo: `AUDITORIA_TECNICA_PAYPAL_AI_HACKATHON.md`, `DIAGNOSTICO_OPERATIVO_FASE_0.md` y los README existentes se usaron como referencia, no se duplicaron.
