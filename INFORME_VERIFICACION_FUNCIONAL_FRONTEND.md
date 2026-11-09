# Informe de verificación funcional del frontend — TallerClaro

> **Estado posterior:** este informe conserva la línea base funcional anterior. Para el estado después de las correcciones locales de Fases 2–9, consulte `MATRIZ_FUNCIONAL_FRONTEND_BACKEND.md`, los informes de fase y la sección de verificación local al final de `INFORME_PRUEBAS_E2E.md`. Los flujos API/DB/proveedores reales siguen sin validarse.

> **Línea base histórica:** el cuerpo original de este informe describe la prueba DEMO previa a las correcciones. El addendum siguiente registra la verificación posterior y los cambios locales de la fase 2.

## Addendum — Correcciones locales de Fase 2

Fecha: 9 de noviembre de 2026.

### Defectos corregidos y evidencia posterior

| Defecto de la línea base | Cambio | Comprobación posterior |
|---|---|---|
| Recibos desbordaba a 390 px | El selector ahora puede encogerse dentro de la toolbar móvil. | Chromium a viewport 390 px: documento 380/380 px; selector x=15..365, ancho 350 px. |
| Order Detail sintetizaba anticipo/saldo 50/50 | La página carga `GET /api/orders/{id}` mediante el cliente y renderiza solo `payments` que el recurso devuelve; DEMO se etiqueta como muestra. | TC-1048 DEMO mostró $9,200 ilustrativos y “No payment records”; ningún renglón inventado de $0/50%. En REAL el fetch está implementado, pero no hubo backend/autenticación para probarlo. |
| Tracking mostraba saldo con mensaje contradictorio | El saldo se deriva solo con total y pago conocidos; DEMO indica que checkout no está disponible, y REAL bloquea checkout si falta saldo o ID. | TC-1050 demo mostró saldo $1,200 y una nota DEMO, sin botón PayPal ni mensaje “no balance due”. |
| Quote Review con campos incompletos | Se distinguen borrador, error de generación y propuesta generada; no se permite aprobar una quote que siga en `draft`. | Stub local: un 503 dejó borrador/error visible; reintentar con 200 mostró partidas y `pending_review`. Sin backend ni IA reales. |
| Query ID no hidrataba la quote | El router conserva query de hash, `useDemoData` la pasa al cliente y el mock verifica el ID. | Quotes → buscar `1050` → `#/customer/quote?id=TC-1050` abrió la quote persistida en el contexto DEMO. |
| Recibos no tenía acceso lateral y DEMO era invisible | Recibos aparece como `Receipts · DEMO`; `DemoNotice` ahora se renderiza; pantallas y copy marcan qué es de muestra. | Link abre la página y aviso visible; en REAL el enlace de recibos no se muestra porque no existe contrato de carga. |
| Summary contable absorbía errores y mostraba ceros | Accounting ahora distingue fallo/carga y ofrece reintento; adaptadores y `formatMoney` conservan valores ausentes como desconocidos. | ESLint/build y aserciones locales; no se simuló respuesta HTTP de fallo en navegador. |
| Credencial Basic fija en frontend | Se eliminó fallback literal; una ruta de taller sin credencial de sesión lanza error local y no envía petición. Se separan las cabeceras/token de cliente y taller. | Inspección de fuente confirma ausencia de `credencial Basic de demostracion incrustada`; flujo REAL sin credencial no probado contra API. Falta login/sesión seguro. |
| Filtros con estados de pedido exclusivos de DEMO | REAL ahora ofrece solo `pending`, `paid`, `in_progress`, `delivered`, `cancelled`; DEMO conserva `quote_sent` y `ready_to_finish`. “Awaiting advance” usa `pending` en REAL. | ESLint/build pasan; dos aserciones Node directas verificaron ambos conjuntos. La prueba Vitest añadida no pudo ejecutarse porque Vitest no está disponible en `node_modules`. |
| Generation failure oculto | La creación conserva la quote como borrador y registra el error en memoria; Review muestra alerta y ofrece reintentar únicamente si GET confirmó `draft`; el servidor vuelve a validar transición. | Build/lint; no se conectó IA ni API. El botón no puede completar REAL sin auth de taller. |
| Dictado sin estados/error específicos | Se mantiene `en-US`, manejo separado de permiso denegado, falta de micrófono, servicio/red y ausencia de voz; se detiene al desmontar. | Con un constructor Web Speech falso, se comprobaron `start`, `stop`, transcripción añadida al texto previo, error `not-allowed`, aria-pressed y `en-US`; sin audio en esa comprobación. |

### Incidente de verificación del micrófono

En el primer intento de preparar una clase de reconocimiento falsa, esa sustitución no sobrevivió a la navegación. El clic posterior ejecutó el reconocedor nativo de Chromium en una pestaña aislada; el navegador reportó permiso concedido y la página recibió una transcripción en inglés, que se agregó al texto previo. No se envió el formulario ni se creó una quote; la pestaña aislada se cerró enseguida. No puedo confirmar si Chromium transmitió audio a un servicio de reconocimiento externo, así que debe tratarse como una posible transmisión accidental fuera del alcance autorizado. No se volvió a activar el reconocedor nativo. Las pruebas siguientes confirmaron previamente `FakeSpeechRecognition` como constructor y usaron solo la clase falsa local.

### Ejecuciones posteriores

- Quote REAL client flow against local stub: create POST had the expected customer/request body and no auth; generate used dummy Basic. A simulated 503 left a visible Draft with unknown total and retry, no approve action. Retry 200 produced pending_review, line items and amounts. Not a real backend/AI verification.

- Seguimiento cliente REAL con stub local: GET quote + GET order llevaron solo X-Customer-Token; la UI mostro pagos devueltos y saldo cero sin checkout. Una asociacion quote/order incorrecta no hizo GET del pedido. Evidencia del cliente HTTP y del guard local, no de aislamiento/auth en el servidor real.

- `node node_modules\eslint\bin\eslint.js src` — exit code 0.
- `VITE_APP_MODE=demo`, `VITE_API_BASE_URL=''`; `node node_modules\vite\bin\vite.js build` — Vite 8.3.5, 61 módulos, build correcto.
- Once aserciones locales con Node — pasaron para formato de importes, medidas, borradores sin importe, contabilidad sin valores inventados y saldo.
- Browser Chromium — Recibos móvil, detalle, quote draft/medidas, aprobación simulada, tracking y lookup por ID. No se observaron llamadas `/api/`.
- Vitest no se ejecutó: `frontend/node_modules/vitest` no existe; la ejecución anterior de pnpm falló por acceso denegado al lock del store. No se instalaron dependencias.

Persisten bloqueos: REAL no se probó; falta autenticación de taller en la app, API y PostgreSQL de pruebas, IA, Channel3 y PayPal Sandbox. Ninguna issue se cerró. Ver [INFORME_CORRECCIONES_FRONTEND_FASE_2.md](INFORME_CORRECCIONES_FRONTEND_FASE_2.md) y [INFORME_PRUEBAS_E2E.md](INFORME_PRUEBAS_E2E.md).

Fecha de la línea base: 9 de noviembre de 2026. La revisión original ejecutó Chromium con datos ficticios y modo DEMO, sin modificar entonces código, configuración, dependencias ni `.env`. El seguimiento posterior de Fase 2 está en el addendum superior; se documentó allí el incidente de dictado nativo.

## 1. Resumen ejecutivo

Vite arrancó correctamente y se verificaron flujos visibles de dashboard, pedidos, cotizaciones, solicitud de cliente, revisión/aprobación, seguimiento, contabilidad, recibos y retorno de pago. En la sesión de navegador todos los datos de negocio fueron fixtures/demo y no se observó tráfico a `/api/`. Por tanto, esta ejecución comprueba comportamiento de interfaz DEMO, no conectividad real con el backend, persistencia PostgreSQL, IA, Channel3 ni PayPal.

Se observaron defectos funcionales concretos: la cotización DEMO aprobada no habilita el checkout; el seguimiento muestra saldo pendiente pero también indica que no hay saldo a pagar; el detalle de pedido presenta renglones de pago de $0 aunque el pedido registra $9,200 pagados; y Recibos desborda horizontalmente a 390 px. El error de generación real de una cotización y el modo REAL no se pudieron validar con servicios ausentes.

El control de dictado aparece en el campo de descripción de la solicitud. El hook usa Web Speech API con idioma fijo `en-US`. Chromium expuso `webkitSpeechRecognition`, pero no se pidió permiso ni se grabó audio: hacerlo podría enviar voz a un servicio del navegador, fuera del alcance autorizado. No hay prueba de transcripción efectiva ni de español. No se encontró un componente o función llamada `speaker`/`speakers`.

No se pudo ejecutar Vitest: `pnpm test -- --reporter=verbose` se detuvo al no poder abrir el lock del store de pnpm; además, no se encontró Vitest en `frontend/node_modules`. El resultado de esas comprobaciones no es un fallo de tests del producto, sino una limitación del entorno instalado.

## 2. Resultado de ejecución

| Comprobación | Resultado |
|---|---|
| Node | `v24.13.1` |
| pnpm | Disponible; el comando de test falla antes de cargar Vitest por `ERR_PNPM_STORE_DIR_OPEN_OPERATION_LOCK` y acceso denegado al archivo `...pnpm-store-operation-locks\all-stores.lock`. |
| Servidor local | Vite `v8.3.5` arrancó mediante `node node_modules/vite/bin/vite.js --host 127.0.0.1`; indicó `http://127.0.0.1:5173/` y `ready in 980 ms`. Se detuvo después de la verificación. |
| Modo | `VITE_APP_MODE=demo`, establecido solo en el proceso de Vite para esta sesión; no se cambió archivo de configuración. |
| Pruebas frontend | No ejecutables en el entorno: `vitest` no está disponible en `frontend/node_modules`; pnpm no pudo abrir su lock local. No se instalaron dependencias. |
| Navegador/consola | Chromium 156 en Windows. Cero mensajes de error de consola reportados durante la sesión. Se revisó el contexto aislado de prueba. |
| Red | No se observaron solicitudes a `/api/` en el navegador durante los flujos DEMO. Los recursos de Vite/app locales sí cargaron. |
| Persistencia | Se probó almacenamiento DEMO en contexto aislado; sus datos se descartaron al cerrar esa pestaña. No se modificó la pestaña/contexto preexistente del usuario. |

El servidor solo se declara iniciado porque se confirmó la salida `ready` y se cargó la aplicación en el navegador. La revisión se limitó a una sesión Chromium; no prueba otros navegadores ni dispositivos físicos.

## 3. Inventario de pantallas y resultado funcional

Rutas observadas en `frontend/src/App.jsx`. Las rutas hash directas pueden existir aunque no estén enlazadas en el menú.

| Pantalla/ruta | Qué muestra e interacciones | Servicio/datos observados | Resultado y brechas |
|---|---|---|---|
| Dashboard `#/dashboard` | Resumen de métricas y pedidos recientes; accesos laterales, navegación y menú móvil. | `useDemoData`/`mockApi` en la sesión. REAL espera servicios de pedidos y resumen según `apiClient`. | Carga fixtures y pedido ficticio local. Menú móvil abrió/cerró; Escape cerró el drawer y devolvió foco al control de apertura. No se validó datos backend. |
| Orders `#/orders` | Tabla/listado, búsqueda, filtros y ordenamiento; acceso al detalle. | DEMO local; REAL espera `GET /api/orders` y paginación del backend. | Búsqueda `Lucia` + estado `In production` redujo la lista al pedido esperado. La UI no demostró navegación por páginas en esta prueba; la fuente previa indica que no envía `limit`/`offset`. |
| Quotes `#/quotes` | Formulario para buscar quote por ID y lista rotulada “Pending customer approval”. | DEMO/lista derivada de fixtures de pedidos. REAL pretende datos de cotización/órdenes, pero no existe endpoint de lista de quotes. | Buscar ID `1048` antes de crear una quote mostró “Quote not found”. Esta lista no prueba un listado backend de cotizaciones. La navegación por query/ID no hidrató una cotización. |
| Request Form `#/customer/new` | Descripción del proyecto, contacto, sugerencias y dictado; valida y envía solicitud. | DEMO usa `mockApi`; REAL hace `POST /api/quotes` y después `POST /api/quotes/{id}/generate`. | Validación/envío DEMO y flujo REAL contra stub probados: error 503 visible como borrador y reintento 200 carga propuesta. Sin backend real, IA ni DB. |
| Quote Review `#/customer/quote` | Descripción, partidas, total, depósito/saldo, búsqueda de catálogo y aprobar/rechazar. | DEMO genera quote/resultado local; REAL espera `GET /api/quotes/{id}`, búsqueda por `q`, generación y approve/reject. | Aprobación creó el pedido demo TC-1050. Datos de medidas y partidas contenían valores por defecto/incompletos: renglones `undefined undefined @ $360`; medidas no coincidían plenamente con lo escrito. Búsqueda `oak` no cargó recomendaciones y no se vio “Apply to Quote”. No fue cotización valorizada desde IA/backend. |
| Customer Tracking `#/customer/tracking` | Estado del pedido, montos abonado/pendiente e historial de pagos; potencial acceso a checkout. | DEMO desde almacenamiento local; REAL debe consultar detalle de pedido con token cliente. | Para TC-1050 mostró total $1,200, pagado $0 y pendiente $1,200, pero el aside dijo que no había saldo a pagar y no mostró checkout. Las condiciones del fixture (sin `orderId`/`remainingBalance` esperado) hacen inconsistente la acción con la cifra presentada. |
| Order Detail `#/order/:id` | Datos del pedido, avance/estado, edición de estado y acciones cancelar/eliminar; panel de pagos. | DEMO local; el servicio REAL dispone de `GET /api/orders/{id}` y `PATCH /api/orders/{id}`. La pantalla no quedó validada contra API. | TC-1048 mostró total $18,400 y $9,200 pagados/$9,200 pendientes. El panel desglosó depósito y saldo ambos en $0, por lo que contradice el resumen. Cambiar a Delivered mostró un diálogo; al confirmar se informó que la entrega requiere pago completo verificado y no está disponible en DEMO. |
| Accounting `#/accounting` | Métricas, asistente y preguntas sugeridas. | DEMO fixtures y respuesta local; REAL espera `GET /api/accounting/summary` y `POST /api/accounting/assistant`. | Se mostró respuesta explícitamente demo, que advierte que costos no están registrados y no puede calcular utilidad. No se probó manejo de errores REAL ni se verificó contabilidad persistida. |
| Receipts `#/receipts` | Selección de pedido, selector de archivos y vista de recibos/gastos. | Solo `mockApi`/DEMO según la UI; no existe endpoint backend de receipts/expenses en routers revisados. | Copy indica que se conserva nombre/metadata, no bytes ni revisión real; datos ilustrativos. No está en los elementos normales de navegación lateral. A 390 px el selector se extendió hasta x=409 (viewport útil 380 px), causando overflow horizontal. |
| Payment Return `#/customer/payment/return` | Recupera intento de pago conocido, verifica resultado y permite seguir con retorno. | REAL pretende `GET /api/payments/{id}` y, cuando aplique, `POST /api/payments/{id}/capture`; sesión de intento local. | Sin intento recuperable informó que no hizo consulta ni inició otro pago. No se probó una captura ni un intento real. No se observó tráfico API. |
| Payment Cancel `#/customer/payment/cancel` | Informa cancelación y ofrece volver a tracking. | Resultado visual local; backend debe ser autoridad para el estado del pago. | En la sesión sin intento, mostró que no había pago recuperable. La ruta por sí sola no verifica cancelación con PayPal. |

### Navegación y cobertura visual

- El menú principal enlaza Dashboard, Orders, Quotes y Accounting. Recibos existe como ruta pero no como acceso lateral regular.
- Se verificaron el acceso al formulario de nueva solicitud, revisión, tracking y detalle de pedido; una navegación directa a retorno/cancelación cubrió el estado sin intento.
- Se probaron validación vacía, envío demo, búsqueda/filtro en Orders, búsqueda de cotización fallida, búsqueda de catálogo, aprobación, error de transición a Delivered, asistente demo y estado de retorno sin intento.
- En viewport móvil de 390 × 844 CSS px, `/orders`, `/quotes`, `/customer/new`, `/customer/quote`, `/customer/tracking`, `/accounting` y `/order/TC-1048` no mostraron overflow de documento. `/receipts` sí. En escritorio no se vio overflow del Dashboard.
- Los resultados no son certificación de accesibilidad, contraste, zoom, lector de pantalla, orientación apaisada ni pruebas en teléfonos. El documento local `frontend/docs/ACCESSIBILITY_RESPONSIVE_REVIEW.md` reporta una revisión anterior a varias anchuras; la medición actual contradice su afirmación de ausencia de overflow en Recibos a 390 px para este checkout.

## 4. Matriz de funcionalidades y pruebas

| Área | Probado en esta sesión | Resultado | Falta para considerar completa |
|---|---|---|---|
| Arranque | Arranque local Vite y apertura en Chromium | Correcto en modo DEMO | Repetir desde el comando pnpm habitual cuando se resuelva el bloqueo del store; no se evaluó despliegue. |
| Enrutamiento | Rutas principales, subrutas cliente y retorno | Renderizan; recepción no tiene enlace lateral y quote por query no rehidrata | Pruebas de todos los enlaces, deep links nuevos, back/forward y refresh en cada ruta. |
| Formularios | Solicitud vacía y válida | Validación visual correcta; DEMO avanza | Validar límites, email, estados durante envío y errores 4xx/5xx en REAL. |
| Cotización | Búsqueda, revisión, catálogo y aprobación DEMO | Funciona solo con fixtures; datos de líneas/medidas incompletos y checkout posterior no aparece | Generación IA real con respuestas/fallos, idempotencia, estados draft, datos null y acceso cliente/taller. |
| Pedidos | Búsqueda/filtro, detalle, diálogo de cambio de estado | UI responde; panel de pagos no concuerda con el resumen; transición no persiste en DEMO | API REAL, paginación completa, error/reintento, GET por ID y PATCH de estados permitidos. |
| Seguimiento/pagos | Tracking de fixture y retorno sin intento | Sin pago funcional de punta a punta; presentación de saldo inconsistente | Token cliente recuperable, intención real Sandbox, retorno/cancelación, captura verificada y recuperación tras timeout. |
| Contabilidad | Dashboard contable y pregunta al asistente DEMO | Mensaje local marcado demo; costes/utilidad no registrados | Summary/assistant backend, error visible, conciliación y definición de gastos. |
| Recibos | Pantalla y selección de archivo visual | Solo simulación metadata; overflow móvil | Subida de bytes segura, endpoints/storage y política de permisos/retención; corrección responsive. |
| Dictado | Presencia del botón y disponibilidad de API en Chromium | Soporte declarado, transcripción no ejecutada | Prueba consentida con micrófono/servicio, español, permisos, errores, append y matriz de navegadores. |
| Errores/consola/red | Errores de consola y tráfico `/api/` | 0 errores de consola; no se vieron llamadas API en DEMO | Ejecución REAL con backend local/fixture autorizado para probar fallos y respuestas HTTP. |

## 5. Componentes simulados frente a reales

### DEMO/local

- `frontend/src/services/mockApi.js` genera respuestas locales y guarda registros DEMO en `localStorage`; la sesión aislada confirmó el flujo de solicitud/aprobación sin `/api/`.
- Métricas de Dashboard/Accounting, lista de pedidos, precios/sugerencias, respuesta del asistente y recibos son fixtures o respuestas simuladas en modo DEMO.
- La página de recibos explicita que el archivo no se sube y que solo se conserva metadata/nombre.
- La aprobación local produce un pedido ficticio, no una fila persistida en PostgreSQL.

### Integración presente en fuente, pero no comprobada como operativa

- `frontend/src/services/apiClient.js` y `http.js` contienen llamadas para quote, order, payment y accounting; la pantalla o adaptador puede no consumir todo el contrato (por ejemplo, Order Detail no utiliza el `getOrder(id)` disponible, según lectura del código).
- La configuración del modo REAL y el cliente HTTP permiten apuntar a API; esta ejecución no configuró URL ni conectó servicio. La mera existencia de método/endpoint no acredita conectividad.
- No se probaron backend, DB, PayPal, IA, Channel3 ni CORS en vivo. El checkout no puede catalogarse como “funciona” con la prueba DEMO observada.

## 6. Dictado de voz por micrófono y “speakers”

- **Ubicación:** botón `Speak` únicamente en el textarea de descripción de `frontend/src/components/customer/RequestForm.jsx`. No se encontró botón de dictado en nombre, email, catálogo, preguntas de accounting u otros campos.
- **Tecnología:** `frontend/src/hooks/useSpeechInput.js` usa `window.SpeechRecognition || window.webkitSpeechRecognition`. No llama a una API backend propia ni usa síntesis de voz. El idioma está fijado a `en-US`, `interimResults=false`.
- **Transcripción:** el código define un handler `onresult` y pasa texto reconocido al callback. Sin embargo, el reconocimiento real no se activó en esta validación; por tanto, no se afirma que haya transcrito correctamente en este navegador.
- **Disponibilidad/permisos comprobados sin captura:** Chromium 156/Windows en `http://127.0.0.1:5173` indicó contexto seguro, expuso `webkitSpeechRecognition` y el permiso `microphone` seguía `prompt`. No se solicitó permiso, no se obtuvo audio y no hubo petición de reconocimiento. Este permiso depende además de HTTPS/origen y de la decisión del usuario.
- **Estado/error según fuente:** el hook ofrece estados de escucha, detención, ausencia de reconocimiento/error y ausencia de habla; `recognition.start()` inicia captura. El error se presenta con mensaje genérico, no distingue permisos denegados, falta de red, servicio no disponible o `no-speech`. Se debe comprobar también que el botón de detener y `onend` limpien el estado en condiciones reales.
- **Preservación del texto:** `useQuoteRequest.appendDescription` agrega la transcripción después del texto existente separada por espacio. Es evidencia de implementación en código, no resultado experimental de voz; no se verificó puntuación, duplicación, selección/cursor ni dictados sucesivos.
- **Español:** no se verifica; la configuración actual `en-US` no selecciona español y no hay selector de idioma localizado. Requiere cambio y pruebas consentidas antes de afirmar soporte.
- **DEMO/REAL:** el mismo control se habilita según disponibilidad del navegador y configuración de app, sin depender del endpoint de quote. No implica que la transcripción sea local ni que DEMO/REAL cambie el proveedor. REAL no se ejecutó.
- **Navegadores móviles:** no probados. No se usó un dispositivo móvil ni navegador móvil; no se infiere compatibilidad móvil a partir de Chromium escritorio.
- **Pruebas automatizadas:** no se encontró prueba dedicada de `useSpeechInput` ni de permisos/resultados de reconocimiento. Los tests existentes de otros módulos no prueban esta función. Vitest tampoco pudo ejecutarse por las limitaciones indicadas.
- **Privacidad de prueba:** se dejó el micrófono sin activar porque Web Speech del navegador puede utilizar servicios de reconocimiento fuera de la app. Esto habría cruzado la restricción de no conectar servicios externos. Resultado: soporte detectado; comportamiento de grabación/transcripción **no verificable en esta sesión**.
- **“Speakers”:** no se encontró componente, export ni identificador `speaker`/`speakers` en `frontend/src`. Tampoco se comprobó funcionalidad de altavoz/reproducción de voz. No debe confundirse con el botón de reconocimiento del micrófono.
- **Issue recomendada:** crear issue específica para “Dictado por voz en formulario de solicitud”. Alcance mínimo: idioma español configurable/definido, compatibilidad documentada, permiso explícito, estados/error accesibles y prueba de texto previo + dictado concatenado; definir claramente si el servicio de reconocimiento del navegador puede transmitir audio y cómo se informa al usuario. Relacionarla con accesibilidad #21 si corresponde; no hay issue específica identificable en la documentación local.

## 7. Errores visuales y funcionales comprobados

1. **Checkout DEMO no disponible tras aprobar:** la quote aprobada genera pedido TC-1050; no aparece `PayPalCheckout` porque el fixture no aporta el identificador numérico que el flujo espera.
2. **Saldo contradictorio en tracking:** cifra restante $1,200 junto con el mensaje “no balance due” y sin acción de pago. Los campos requeridos por la rama de checkout no concuerdan con el fixture.
3. **Pagos ficticios en Order Detail:** el pedido muestra $9,200 pagados, mientras los dos renglones del panel indican $0 cada uno. No representa historial real de transacciones.
4. **Quote Review presenta datos incompletos como si estuvieran listos:** renglones con `undefined` y medidas por defecto distintas de lo ingresado; la cotización demo aparece lista sin precio/catalogación real.
5. **Recibos desborda en móvil:** ancho del select ~394 px dentro del viewport útil de 380 px a 390 CSS px.
6. **Búsqueda por ID en Quotes no encuentra fixture 1048:** no se probó que la pantalla resuelva el ID de query ni cargue la quote al navegar.
7. **Sin acceso normal a Recibos:** ruta disponible, pero falta enlace visible en el sidebar probado.

No aparecieron errores en consola en la sesión. Esto no elimina los defectos de lógica/presentación observados ni valida fallos del API REAL.

## 8. Brechas frontend-backend por flujo

| Flujo | Backend esperado en modo REAL | Comprobación de esta sesión | Brecha restante |
|---|---|---|---|
| Crear/generar quote | `POST /api/quotes`, `POST /api/quotes/{id}/generate`, `GET /api/quotes/{id}` | No invocado en DEMO | Verificar auth de taller, error de generación visible, quote draft vs propuesta lista y forma de los items. |
| Listar/lookup quotes | GET de quote individual existe según cliente; no hay listado backend de quotes | Quotes usa fixtures de pedidos y búsqueda local falló | Definir endpoint/lista, resolver query ID, permisos/credenciales y estados correctos. |
| Aprobar/rechazar | `POST /api/quotes/{id}/approve`, `POST /api/quotes/{id}/reject` | Aprobación local solamente | Verificar token/ownership, respuesta Order y navegación al pedido persistido; prueba de rechazo no ejecutada. |
| Orders list/detail | `GET /api/orders?limit&offset`, `GET /api/orders/{id}` | No invocado | Paginación, total y detalle por ID deben consumirse; confirmar que la pantalla use pagos y saldo del detalle. |
| Actualizar pedido | `PATCH /api/orders/{id}` | Acción demo con bloqueo visible para Delivered | Mapear solo estados admitidos y separar reglas de pago; probar 409/422. |
| Pagos | `POST /api/orders/{id}/payments`, `GET /api/payments/{id}`, `POST /api/payments/{id}/capture` | Sin intento recuperable, sin llamada | Crear intento y reconciliar respuesta incierta requiere entorno de prueba y Sandbox autorizado. |
| Accounting | `GET /api/accounting/summary`, `POST /api/accounting/assistant` | Respuesta local | Mensajes de error REAL, cifras respaldadas y costos/gastos requieren integración/modelo adicional. |
| Receipts/expenses | No se encontraron endpoints/backend | Solo UI demo/metadata | Acordar modelo, permisos, bytes/storage y endpoints antes de afirmar carga real. |
| Voz | No existe endpoint propio de transcripción observado; hook Web Speech API | Solo capacidad global detectada; no captura | Configurar idioma, probar permisos/compatibilidad y documentar proveedor/privacidad. |

La presencia de rutas backend y adaptadores en el árbol no se usó como evidencia de que respondan. No se intentó conexión HTTP externa ni PostgreSQL.

## 9. Issues #10–#28

No se consultó GitHub por la restricción de no contactar servicios externos. Los títulos, estados y criterios oficiales no están disponibles para todas las issues en los documentos locales; las asignaciones siguientes son provisionales y no reemplazan el cuerpo oficial.

| Issue | Clasificación | Evidencia y prueba faltante para cerrar |
|---|---|---|
| #10 | **No verificable** | No hay alcance/título/cuerpo local identificable ni criterios oficiales; consultar issue sería necesario. |
| #11 | **No verificable** | Igual: sin alcance ni criterios locales verificables. |
| #12 | **No verificable** | Igual: sin alcance ni criterios locales verificables. |
| #13 | **No verificable** | Igual: sin alcance ni criterios locales verificables. |
| #14 | **No verificable** | Igual: sin alcance ni criterios locales verificables. |
| #15 | **Implementada parcialmente** | Request y aprobación DEMO observados; datos mock incompletos y sin generación/persistencia real. Faltan criterios oficiales y flujo REAL con auth, errores, generación, rechazo y datos backend. |
| #16 | **Implementada parcialmente** | Dashboard/listado/filtro/detalle y acción de estado presentes en la UI; detalle exhibió pagos contradictorios y la acción demo bloqueó entrega. Falta paginación/API/auth y aceptación oficial. |
| #17 | **No verificable** | No hay alcance/título/cuerpo local identificable; no es posible asociar evidencia funcional con rigor. |
| #18 | **Bloqueada por infraestructura** | UI/API de pago existe en fuente, pero checkout real no se verificó; checkout DEMO no apareció tras aprobar y retorno no tenía intento. Para cierre: criterios oficiales, backend+DB de prueba y PayPal Sandbox, no credenciales Live. |
| #19 | **Pendiente de integración** *(provisional)* | Documentación local la menciona junto a trabajo compartido/contratos, sin cuerpo oficial accesible. Hace falta acordar contrato, auth, errores y evidencias integradas. |
| #20 | **Implementada parcialmente** | Rutas cliente y tracking DEMO funcionan visualmente; saldo se contradice y no hay continuidad REAL probada. Para cerrar: vínculo/token, pedido backend, datos de pago verificados y criterios oficiales. |
| #21 | **Implementada parcialmente** | Navegación móvil y foco/Escape se probaron; Receipts tiene overflow a 390 px. Falta corregirlo, probar teclado/lector/zoom y repetir matriz; documento previo no basta como aceptación actual. |
| #22 | **Implementada parcialmente** | DEMO explícito y mocks identificables; esta ejecución confirma funcionamiento local. Persisten simulaciones y sin prueba REAL; falta cotejar requisitos oficiales/documentación de setup actual. |
| #23 | **Pendiente de integración** *(provisional)* | Documentación local la agrupa con tareas compartidas; sin alcance oficial verificable. Faltan cierre de contratos y pruebas integradas atribuibles. |
| #24 | **No verificable** | No hay definición local ni criterio oficial disponible; sin acceso GitHub no se puede determinar estado. |
| #25 | **No verificable** | Igual: falta alcance y evidencia oficial. |
| #26 | **No verificable** | Igual: falta alcance y evidencia oficial. |
| #27 | **No verificable** | Igual: falta alcance y evidencia oficial. |
| #28 | **No verificable** | Igual: falta alcance y evidencia oficial. |

No recomiendo cerrar ninguna issue con esta ejecución. Para issues con pantalla visible, la prueba fue DEMO parcial y no demuestra criterios de persistencia/seguridad/servicio; para las restantes, ni siquiera está confirmado su alcance. La documentación local (`frontend/docs/FRONTEND_AUDIT.md`, `IMPLEMENTATION_ROADMAP.md`, `API_CONTRACT.md`) también advierte que faltaban cuerpos/criterios oficiales y contiene observaciones históricas que pueden estar superadas por el checkout actual.

El dictado de voz requiere una issue dedicada: crearla y vincularla a #21 si el alcance oficial de #21 incluye entradas por voz. No asigno un número existente sin evidencia.

## 10. Orden recomendado de correcciones

1. **Confirmar criterios de issues y contrato/auth.** Obtener cuerpos oficiales de #10–#28 en una fase permitida; acordar autenticación de taller/cliente y respuestas canónicas.
2. **Resolver bloqueos de API y seguridad antes de REAL.** Eliminar credencial de taller embebida, definir login/sesión/token y orígenes CORS; probar auth/error sin proveedor externo usando clientes simulados.
3. **Hacer veraz el ciclo de cotización.** Diferenciar draft de quote generada, presentar fallo de generación, campos nulos y errores; arreglar carga por ID/query, listado y estados.
4. **Corregir el seguimiento de pedidos.** Usar GET por ID, mostrar pagos/saldo de respuesta en lugar de renglones 50/50 ficticios; unificar estados permitidos y paginar pedidos.
5. **Completar recuperación/checkout.** Diseñar recuperación de intento incierto e idempotencia; después probar con DB descartable y PayPal Sandbox autorizado.
6. **Mostrar contabilidad con errores explícitos.** No convertir falla en ceros; aclarar contrato financiero y dejar fuera gastos/utilidad hasta que exista soporte.
7. **Definir e implementar recibos/gastos.** Solo tras aprobar modelo, permisos, almacenamiento, límites y retención; reparar al mismo tiempo el overflow responsive de Recibos.
8. **Dictado de voz.** Crear issue específica; definir español, consentimiento/privacidad del proveedor, permisos, estados accesibles y compatibilidad antes de afirmar que está operativo.
9. **Repetir una matriz funcional reproducible.** Ejecutar unitarios de frontend, pruebas de navegador y accesibilidad; luego contrato con API/DB de prueba y, por último, E2E Sandbox.

## 11. Evidencia, límites y fuentes locales

**Archivos de interfaz y servicios revisados:**

- `frontend/src/App.jsx`, layout y páginas `DashboardPage`, `OrdersPage`, `QuotesPage`, `ReceiptsPage`, `AccountingPage`, `OrderDetailPage`, `RequestOrderPage`, `QuoteReviewPage`, `OrderTrackingPage`, `PaymentReturnPage`.
- `frontend/src/components/customer/RequestForm.jsx`, `frontend/src/hooks/useSpeechInput.js`, `frontend/src/hooks/useQuoteRequest.js`.
- `frontend/src/services/http.js`, `apiClient.js`, `adapters.js`, `sessionStore.js`, `mockApi.js`.
- `frontend/docs/ACCESSIBILITY_RESPONSIVE_REVIEW.md`, `FRONTEND_AUDIT.md`, `IMPLEMENTATION_ROADMAP.md`, `API_CONTRACT.md`.

**Limitaciones:**

- No se leyó `.env` ni se usaron credenciales; no se configuró API REAL. Ningún endpoint fue considerado operativo por existir en código.
- En la prueba DEMO original no hubo permiso ni grabación; el incidente posterior con Web Speech nativo está descrito en el addendum de Fase 2. El dictado en español y en móviles queda sin verificar.
- No se accedió a GitHub; issues #10–#28 no pueden recibir un estado oficial en ausencia de sus cuerpos y criterios.
- No se ejecutó Vitest por el fallo de acceso al store y la falta del paquete instalado; no se instalaron dependencias.
- Una sesión Chrome y fixtures locales no equivalen a pruebas exhaustivas de todas las combinaciones de interacción, resolución, navegador, persistencia y error.

**Comandos ejecutados relevantes:**

```text
pnpm test -- --reporter=verbose
→ ERR_PNPM_STORE_DIR_OPEN_OPERATION_LOCK: acceso denegado al lock del store de pnpm; Vitest no llegó a ejecutarse.

node node_modules/vite/bin/vite.js --host 127.0.0.1  (desde frontend, con VITE_APP_MODE=demo en el proceso)
→ VITE v8.3.5 ready in 980 ms; http://127.0.0.1:5173/; aplicación cargada en Chromium.
```

No se instalaron paquetes, no se cambió fuente ni configuración y no se ejecutaron pruebas contra infraestructura.
