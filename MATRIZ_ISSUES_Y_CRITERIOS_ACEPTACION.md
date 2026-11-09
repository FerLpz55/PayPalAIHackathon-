# Matriz de issues y criterios de aceptación — TallerClaro

Actualizada: 9 de noviembre de 2026. Los cuerpos, títulos, estado remoto, owner y criterios oficiales de #10–#28 no se pudieron confirmar. Las descripciones parciales de `frontend/docs/FRONTEND_AUDIT.md` y `IMPLEMENTATION_ROADMAP.md` son provisionales. No se cerró ninguna issue.

| Issue | Criterio de aceptación local/provisional | Estado del checkout | Archivos/evidencia | Dependencia y prueba para cierre |
|---|---|---|---|---|
| #10 | No disponible | No verificable | Sin referencia local encontrada | Cuerpo/criterios oficiales; prueba acorde al alcance. |
| #11 | No disponible | No verificable | Sin referencia local encontrada | Ídem. |
| #12 | No disponible | No verificable | Sin referencia local encontrada | Ídem. |
| #13 | No disponible | No verificable | Sin referencia local encontrada | Ídem. |
| #14 | No disponible | No verificable | Sin referencia local encontrada | Ídem. |
| #15 - Quote review/approval (provisional) | Quote completa, validada, aclaraciones, aprobar/rechazar y persistir; official issue criteria unavailable | Parcial: DEMO y error/retry REAL probados con stub; missing_info visible; sugerencias aisladas por quote; formulario conserva aclaracion ante fallo; cliente no puede enviarla sin Basic de taller. Sin API/IA real ni aprobacion persistida. | QuoteReviewPage, RequestForm, apiClient, adapters; prueba browser local | Definir auth/contrato de aclaracion cliente; API/IA/DB de prueba; verificar persistencia, approve/reject, retry y errores contra backend. |
| #16 - Dashboard/order management (provisional) | Lista/detalle/estado de ordenes persistidos y autorizados | Parcial: paginacion, summary global y Order Detail/PATCH conectados; pruebas solo con stub local | DashboardPage, OrdersPage, OrderDetailPage, apiClient; DEMO y stub local | Backend/auth/DB; validar list/detail/PATCH/transiciones/pagos contra API de prueba. |
| #17 | No disponible | No verificable | Sin referencia local encontrada | Cuerpo/criterios oficiales. |
| #18 ? PayPal checkout (provisional) | Intencion, aprobacion, captura verificada, errores/reintento/idempotencia | Bloqueado por Sandbox/DB; gate visual terminal implementado y probado con stub; API todavia no bloquea pedidos cancelados/eliminados | PayPalCheckout, apiClient, PaymentReturnPage, OrderTrackingPage; nunca se ejecuto proveedor | PayPal Sandbox, API y DB staging; validar rechazo backend cancelled/deleted, importe/moneda, duplicados, timeout y retorno. |
| #19 — Shared integration (provisional) | Alcance compartido no identificable | Pendiente de integración; criterio oficial no verificable | Referida por roadmap local a contratos y coordinación | Acordar owner/issue body; pruebas de contrato compartidas. |
| #20 - Customer navigation/tracking (provisional) | Navegacion quote->order, estado/pago server-backed y aislamiento por cliente | Parcial: cambio de ID y de token en mismo ID ocultan quote anterior ante 403; requests obsoletas descartadas. Tracking y estados probados con stub; ownership real y token recuperable sin verificar. | useHashRoute, useDemoData, OrderTrackingPage; Chromium/stub local | Politica de token/DB/API; probar sesiones distintas, ownership y pagos contra backend de prueba. |
| #21 — Accessibility/responsive (provisional) | Accesibilidad y reflow verificados, no certificación | Parcial: overflow de recibos corregido a 390 px; mic fake y nav funcionales; sin pruebas físicas/AT | app.css, hook de voz, navegación | Browser/AT matriz oficial; corregir hallazgos adicionales; autorización antes de mic nativo. |
| #22 — Demo separation/documentation (provisional) | DEMO identificable y no presentada como REAL | Parcialmente implementada y probada local: avisos demo visibles, sin calls API, sin checkout/pagos reales | DemoNotice, mockApi, páginas; Chromium DEMO | Revisar criterios oficiales; contrastar modos/config de despliegue. |
| #23 — Shared task (provisional) | Scope compartido/acceptance desconocidos | Pendiente de integración; oficial no verificable | Mencionada por docs locales junto a coordinación | Issue body, ownership y evidencia conjunta. |
| #24 | No disponible | No verificable | Sin referencia local encontrada | Cuerpo/criterios oficiales. |
| #25 | No disponible | No verificable | Sin referencia local encontrada | Ídem. |
| #26 | No disponible | No verificable | Sin referencia local encontrada | Ídem. |
| #27 | No disponible | No verificable | Sin referencia local encontrada | Ídem. |
| #28 | No disponible | No verificable | Sin referencia local encontrada | Ídem. |

### Issue nueva recomendada

**Dictado `en-US` en solicitud de cliente.** Criterios propuestos: registrar permiso y compatibilidad por navegador; iniciar/detener; concatenar al texto previo; estados accesibles; errores de denegación, falta de micrófono, red/servicio y silencio; pruebas solo con mock automatizado. Aclarar que el reconocedor nativo puede transmitir audio a un proveedor del navegador. No cambiar el idioma. No asignar número hasta crear la issue en GitHub.

Para cerrar cualquier issue, sustituir el criterio provisional por el body oficial, enlazar commit/PR, prueba reproducible, y separar resultado DEMO/mocks de API/DB/servicio real. No se cierra una integración externa con solo tests unitarios.

### Actualización de evidencia — Fase 7

- **#15 (criterio provisional):** Quote Review ya muestra las medidas inglesas reconocidas por el adaptador; la regresión se reprodujo antes del cambio y la vista se comprobó después con datos DEMO. El test Vitest está añadido, pero no ejecutado porque el runner no está disponible localmente. Falta verificación automatizada y REAL para afirmar cobertura completa.
- **#21 (criterio provisional):** revisión puntual de ocho rutas a 320 px y Request en 768/1280 px sin overflow de página; navegación móvil comprobada a 390 px. Sigue parcial: no cubre todos los estados/textos, dispositivos reales, Safari/Firefox ni tecnología asistiva.
- La evidencia y limitaciones de esta fase están en [Informe Fase 7](INFORME_CORRECCIONES_FRONTEND_FASE_7.md). Ninguna issue se cerró ni se obtuvo su criterio oficial.

### Autenticación de taller — evidencia Fase 8

El cliente actual no tiene Basic Auth fijo. Con modo REAL y sin credenciales, Dashboard mostró que la solicitud no se envió; Network no registró llamadas `/api/`. El flujo sigue sin ser utilizable porque no existe UI que establezca `workshopCredentials`. No se asigna a una issue específica porque no se obtuvo el body oficial de #10–#28. Ver [Informe Fase 8](INFORME_VERIFICACION_AUTH_FRONTEND_FASE_8.md).

### Login de taller — evidencia Fase 9

La UI ya tiene acceso Basic en memoria, Sign out, bloqueo de datos REAL sin sesión y expiración al 401. Evidencia local solo con stub loopback; no valida FastAPI ni credenciales de despliegue. No se asignó a una issue concreta por falta del body oficial de #10–#28; no se cerró ninguna. [Informe Fase 9](INFORME_IMPLEMENTACION_LOGIN_TALLER_FASE_9.md).

### Consulta oficial y estado de verificacion para publicacion

Se intento consultar el repositorio oficial y la lista de issues/PR. La pagina publica del repositorio abre, pero las vistas de issues y pull requests no se recuperaron; `gh auth status` reporto invalido el token configurado y `git ls-remote` no pudo conectar a github.com:443. Por tanto, los criterios oficiales y la existencia de un PR relacionado siguen **NO VERIFICABLES**. Las asociaciones #15–#22 de esta matriz son hipotesis basadas en documentos locales, no mapeos oficiales confirmados. No se usaron referencias de cierre automatico ni se cerro issue alguna.

La suite backend revisada en esta publicacion obtuvo **314 passed**; el frontend obtuvo lint/build exitosos, pero Vitest no se ejecuto. La evidencia local no satisface criterios que exijan API, PostgreSQL o proveedores reales.
