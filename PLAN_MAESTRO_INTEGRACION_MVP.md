# Plan maestro de integración para el MVP — TallerClaro

Actualizado: 9 de noviembre de 2026. Este documento coordina entregas y remite a la [auditoría técnica](../AUDITORIA_TECNICA_PAYPAL_AI_HACKATHON.md), [plan Fase 1](PLAN_INTEGRACION_FRONTEND_BACKEND_FASE_1.md), [informe funcional](INFORME_VERIFICACION_FUNCIONAL_FRONTEND.md) y [correcciones frontend Fase 2](INFORME_CORRECCIONES_FRONTEND_FASE_2.md); no duplica su matriz HTTP detallada.

## Estado ejecutivo

Frontend DEMO local se ejecuta en Chromium y build/lint pasan. Login de taller Basic en memoria ya implementado y probado con stub loopback; falta validar con FastAPI de staging. Todavía no hay MVP integrado verificado: REAL no se conectó a infraestructura real; PostgreSQL/persistencia, AI, Channel3 y PayPal Sandbox no se comprobaron. Issues no se cerraron.

## Fases y puertas de aceptación

| Fase | Alcance/orden | Dependencias | Criterio para avanzar |
|---|---|---|---|
| 0. Baseline local (actual) | Rama/cambios, entorno, reportes previos, issues disponibles, tests y DEMO | Checkout local | Inventario reproducible; cambios de usuario identificados; no inspeccionar secretos. Estado actualizado en informes de correcciones Fases 2-4. |
| 1. Contrato y auth | Credencial fija retirada; frontend Basic en memoria, HTTPS y logout/401 implementados; auth cliente, roles y CORS pendientes | Cuenta de taller de prueba, API HTTPS de staging y contrato de cliente/token | Cliente fail-closed y login positivo/negativo probados con stub. Falta validar auth, roles, ownership y TLS/CORS contra FastAPI de prueba. |
| 2. Cotizaciones | Create -> generate -> GET por ID -> refine/retry -> approve/reject; distinguir draft/info/pending_review/approved/rejected | Fase 1; AI solo para validacion externa | Draft no se presenta como lista; fallo conserva quote y detalles del cliente, no duplica; retry seguro; valores ausentes no son cero. Cliente no puede enviar aclaraciones con Basic actual: definir contrato antes de conectar el boton. Lista solo cuando exista endpoint. |
| 3. Clientes | Acceso de quote/orden por link recuperable y aislamiento por recurso | Politica de token, canal de entrega, DB descartable | Sesion nueva autorizada accede solo a su recurso; cambio de ID/sesion oculta datos viejos y errores visibles; expiracion/revocacion se explican. UI scope probado con stub; ownership real pendiente. |
| 4. Orders | GET list paginado, detalle por ID, PATCH transiciones | Login Basic frontend; API disponible; DB descartable | OrdersPage envía limit/offset y presenta total/páginas; Dashboard usa summary global; probados con stub local. Falta validarlos contra API+DB de prueba. |
| 5. Pagos | Crear intencion, return/cancel, consultar/capturar, recuperacion de estado incierto | Auth customer; DB descartable; PayPal Sandbox y cuentas de prueba | Solo backend confirma; importe/moneda/IDs verificados; idempotencia, timeout, doble submit y sesion perdida cubiertos; nunca Live. Tracking no ofrece checkout para cancelled/deleted; el backend debe aplicar la misma regla. |
| 6. Contabilidad | Summary y assistant, errores explícitos, conciliación | Órdenes/pagos persistidos | Totales concilian con pagos confirmados; summary fallido no se muestra como cero; no declarar utilidad sin gastos. |
| 7. Recibos/gastos | Contrato, permisos, bytes/storage, review y contabilidad | Definición funcional + DB/storage autorizado | Carga bytes real segura y auditada, límites/retención; demo claramente separado. Hoy no hay endpoints. |
| 8. E2E y entrega | Request → quote → approve → order → Sandbox → tracking → summary | Todas las anteriores en staging | Repetición desde ambiente limpio, fallos/retry y aceptación oficial de issues; evidencia guardada, sin secretos en logs. |

## Trabajo que puede continuar localmente

1. Añadir pruebas Vitest versionadas y corregir su disponibilidad local sin instalar paquetes hasta autorización.
2. Pruebas de componentes/adaptadores, query-ID, estados draft, errores no cero, detalles sin pagos y mock localStorage.
3. Eliminar dependencias UI de lista parcial en Orders/Quotes; revisar navegación, a11y y copy demo.
4. Probar el login Basic en memoria con FastAPI de staging HTTPS y una cuenta temporal autorizada; evaluar BFF/cookie HttpOnly como evolución antes de producción.
5. Expandir pruebas fake Web Speech sin activar el reconocedor nativo; mantener `en-US`.

## Dependencias bloqueantes

- Backend HTTPS de staging, cuenta temporal autorizada y flujo de recuperación/entrega customer token.
- API local o de staging segura y accesible; autenticación Basic segura o decisión sobre sustitución.
- Base PostgreSQL de prueba descartable identificada, schema/version y política explícita de migraciones.
- Credenciales Sandbox AI/PayPal/Channel3 y URLs de staging para validar únicamente los proveedores autorizados; todavía no se usan.
- Seguimiento de criterios oficiales #10–#28 en [matriz de issues](MATRIZ_ISSUES_Y_CRITERIOS_ACEPTACION.md); completar trabajo abierto #14, #17–#19, #23, #27 y #28.

## Estado de la evidencia

- Frontend: informes FASE_2.md a FASE_6.md; lint/build exitosos; pruebas Chromium DEMO y REAL contra stubs locales, sin proveedor ni persistencia real.
- E2E: `INFORME_PRUEBAS_E2E.md`; no existe prueba frontend↔backend/DB/PayPal ejecutada.
- Servicios/credenciales: `PENDIENTES_INFRAESTRUCTURA_Y_CREDENCIALES.md`.
- Issues: `MATRIZ_ISSUES_Y_CRITERIOS_ACEPTACION.md`; no cierre automático.

### Fase 7

Se corrigió la extracción de dimensiones en inglés dentro de Quote Review y se revisó responsive en Chromium. Evidencia y límites en [Informe Fase 7](INFORME_CORRECCIONES_FRONTEND_FASE_7.md). El test Vitest está añadido pero pendiente de ejecución por falta del binario local; API, DB y proveedores externos siguen sin verificarse.

### Actualización Fase 8 — autenticación

En la Fase 8 el cliente fallaba cerrado, pero aún no tenía login. Esa conclusión fue reemplazada por la implementación documentada en Fase 9: Basic en memoria, HTTPS requerido, logout y expiración. La integración con FastAPI real sigue pendiente.

### Login de taller actualizado — Fase 9

El usuario eligió Basic en memoria. La UI, comprobación read-only de acceso, logout, bloqueo antes de sesión y expiración de credencial están implementados; positivo/negativo verificados contra stub loopback. Falta FastAPI HTTPS de staging y cuenta autorizada para demostrar integración real. Ver [Informe Fase 9](INFORME_IMPLEMENTACION_LOGIN_TALLER_FASE_9.md).

### Verificacion local para preparar publicacion — 9 de noviembre de 2026

- Desde `Backend/`, Python 3.11.10: `.venv/Scripts/python.exe -m pytest -v -p no:cacheprovider --basetemp=.pytest-tmp-publication-full` -> **314 passed**. El directorio temporal quedo bajo `Backend/`; las pruebas no usaron PostgreSQL ni servicios externos.
- Frontend: ESLint directo -> exit 0; `vite build` directo -> exit 0, 62 modulos transformados. `pnpm run test/lint/build` no pudo adquirir el lock del store global en el sandbox. Vitest no esta instalado; no se instalaron dependencias.
- Se consultaron issues y PR públicos vía API: #24–#26 son PRs fusionados y no había PR abierto antes de esta publicación. El CLI `gh` tiene un token inválido y la sesión web está cerrada; la creación del PR sigue pendiente de autenticación interactiva.
