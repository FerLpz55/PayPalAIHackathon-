# Informe de correcciones frontend — Fase 2

Fecha: 9 de noviembre de 2026. Alcance: correcciones locales de interfaz/cliente verificadas en DEMO, sin backend, PostgreSQL ni proveedores externos.

## Resultado

Se corrigieron brechas visibles en el seguimiento y detalle de órdenes, cotizaciones, navegación, medidas, errores contables, dictado y vista móvil. DEMO sigue usando mocks/localStorage; sus valores ahora se identifican como ilustrativos y no muestran transacciones PayPal ficticias como pagos reales.

### Cambios

- **Autenticación HTTP:** eliminado `credencial Basic de demostracion incrustada` del fallback Basic. Las rutas de taller sin credencial en sesión fallan localmente con “No request was sent”. Las llamadas de cliente y taller ya no mezclan automáticamente el customer token con Basic. No existe todavía pantalla/login ni fuente segura que establezca las credenciales de taller.
- **Cotizaciones:** hash router conserva query; el ID consultado se pasa al cliente/mock y abre la quote encontrada. UI representa draft, información pendiente, review, approved y rejected; draft REAL no se puede aprobar. La generación fallida que deja draft puede mostrar error y reintentar solo mientras el estado actual recibido sea draft. Sin credencial del taller el reintento falla explícitamente antes de red.
- **Datos faltantes:** `extractMeasurements` no rellena medidas inventadas; los adaptadores no calculan splits 50/50 ni convierten importes/campos ausentes en cero; `formatMoney` distingue cero conocido de valor desconocido.
- **Órdenes/pagos:** detalle de taller invoca `apiClient.getOrder(id)` y pinta únicamente `payments` de la respuesta. Tracking deriva saldo solo si total/pagado son conocidos. DEMO oculta checkout real y aclara que sus importes son muestra. `mutate` devuelve el resultado de la acción, corrigiendo el redirect tras borrar.
- **DEMO/REAL:** DemoNotice ahora renderiza. Copy de Dashboard, solicitud, quote, tracking, detalle y contabilidad no promete IA/precios/pagos reales en DEMO. Recibos queda accesible como `Receipts · DEMO`, no como característica de REAL. Búsqueda/refinamiento de catalogación está deshabilitada en demo y los errores en REAL se presentan.
- **Contabilidad:** errores del summary se muestran y ofrecen retry; datos inexistentes quedan como raya en lugar de cero supuesto. Asistente identifica respuesta de demo.
- **Dictado:** idioma `en-US` conservado. Constructor se consulta al iniciar para soportar prueba/adaptadores tardíos; hay mensajes diferenciados para permiso denegado, servicio/red, micrófono ausente y silencio; captura se detiene al cerrar el formulario.
- **Responsive:** selector de Recibos se ajusta a la toolbar en móvil.
- **Estados de pedidos por modo:** el filtro REAL solo ofrece `pending`, `paid`, `in_progress`, `delivered` y `cancelled`, conforme a los estados de pedidos del backend; los estados fixture `quote_sent` y `ready_to_finish` siguen disponibles solo en DEMO. El contador “Awaiting advance” también usa únicamente `pending` en REAL.

## Archivos frontend modificados

`frontend/src/App.jsx`; `components/accounting/AccountingAssistant.jsx`; `components/customer/{HowItWorks,RequestForm}.jsx`; `components/layout/Sidebar.jsx`; `components/ui/DemoNotice.jsx`; `hooks/{useDemoData,useHashRoute,useSpeechInput}.js`; `pages/{AccountingPage,DashboardPage,OrderDetailPage,OrdersPage,QuotesPage}.jsx`; `pages/customer/{OrderTrackingPage,QuoteReviewPage}.jsx`; `services/{adapters,apiClient,http,mockApi}.js`; `services/__tests__/adapters.test.js`; `styles/app.css`; `utils/{constants,format}.js`; nuevos `utils/__tests__/{format,orderStatuses}.test.js`.

No se modificaron componentes/backend, credenciales, archivos `.env`, package manifests ni locks en esta fase. Hay cambios previos locales en otros archivos del repo; se conservaron.

## Verificación

- ESLint: `node node_modules\eslint\bin\eslint.js src` — exit 0.
- Build: `VITE_APP_MODE=demo`, `VITE_API_BASE_URL=''`; `node node_modules\vite\bin\vite.js build` — Vite 8.3.5, 61 módulos transformados, éxito.
- Tras separar estados DEMO/REAL: ESLint exit 0; build DEMO exitoso; dos aserciones directas Node verificaron que REAL contiene solo los cinco estados actuales de órdenes y DEMO conserva `quote_sent`/`ready_to_finish`. La prueba Vitest correspondiente está añadida, pero Vitest no está instalado en `node_modules` y no se ejecutó.
- Once aserciones locales Node pasaron: `formatMoney`, extracción de medidas, quote draft con total null, summary vacío y cálculo de saldo conocido/desconocido.
- Chromium aislado: Recibos a 390 px sin overflow (documento 380 px, select 350 px); Order Detail sin payment splits; búsqueda ID → quote; quote draft con medidas indicadas y sin `undefined`; simulación de aprobación → tracking con saldo correcto y sin checkout; dictado fake probó start/stop, `en-US`, append preservando texto previo y error `not-allowed`. No se observó tráfico `/api/`.
- Vitest no se ejecutó: paquete no encontrado en `frontend/node_modules`; pnpm tiene error de acceso al lock de su store. Los archivos de prueba se añadieron/actualizaron pero faltan por ejecutar cuando el runner esté accesible.

## Incidente del dictado

En el primer intento de usar una clase falsa, la sustitución no persistió al navegar y el clic ejecutó Web Speech nativo en Chromium. El permiso apareció concedido y el browser produjo una transcripción en inglés, añadida a texto previo; no se envió el formulario ni se creó una quote. No se puede confirmar si el audio salió a un servicio de reconocimiento externo; debe tratarse como posible transmisión accidental. Se cerró enseguida la pestaña/contexto aislado y no se volvió a activar el reconocedor nativo. Las pruebas posteriores verificaron el constructor falso antes de cada clic y no usaron audio.

## No cubierto / aceptación pendiente

- Flujo REAL de quote y retry: falta login/sesión de taller; backend requiere Basic. No se usó IA.
- Auth de cliente de otra sesión, API/DB, transacciones reales, CORS desplegado, pagos, captura y recuperación incierta.
- Vitest y automatización de navegador versionada. La verificación de navegador fue manual en Chromium local, no prueba E2E backend.
- Micrófono físico/permisos reales, idioma distinto a inglés, Safari/Firefox/móvil. No se repetirán sin autorización explícita.
- Recibos/gastos reales y Channel3.

No se cerraron issues. Ver [matriz de issues](MATRIZ_ISSUES_Y_CRITERIOS_ACEPTACION.md), [pruebas](INFORME_PRUEBAS_E2E.md) y [bloqueos](PENDIENTES_INFRAESTRUCTURA_Y_CREDENCIALES.md).
