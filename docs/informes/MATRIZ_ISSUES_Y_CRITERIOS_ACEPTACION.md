# Matriz de issues y criterios de aceptación — TallerClaro

Actualizada: 9 de noviembre de 2026. Títulos, estados y criterios se consultaron en el API público oficial del repositorio. #24–#26 son PRs ya fusionados, no issues. Esta tabla registra la evidencia del checkout y esta iteración; no altera ni cierra issues. Los criterios se resumen del cuerpo oficial.

| Issue | Criterio oficial resumido | Estado GitHub | Evidencia en checkout/esta iteracion | Pendiente para aceptar criterio |
|---|---|---|---|---|
| [#10](https://github.com/FerLpz55/PayPalAIHackathon-/issues/10) PostgreSQL | Conexion de FastAPI, esquema comparado, crear/leer quote, errores sin secretos | Cerrada | Repositorios y suite fake-backed; 314 tests pasan | Base de pruebas aislada, inspeccion de esquema y persistencia real no comprobadas |
| [#11](https://github.com/FerLpz55/PayPalAIHackathon-/issues/11) Formulario API | POST de solicitud guardada, error/reintento, prueba con DB | Cerrada | Solicitud y generation se ejercitaron con stub; backend suite pasa | Probar POST y persistencia con FastAPI/PostgreSQL aislados |
| [#12](https://github.com/FerLpz55/PayPalAIHackathon-/issues/12) Consulta de solicitud | Recuperar por ID tras recarga, error claro, DB de pruebas | Cerrada | Navegacion por ID y quote con stub/DEMO; query route corregida | Recuperacion/persistencia real y token/ownership en API |
| [#13](https://github.com/FerLpz55/PayPalAIHackathon-/issues/13) Acceso | Aislamiento por cliente, autenticacion/taller y pruebas permitidas/denegadas | Cerrada | Basic en memoria, gate fail-closed y 401/logout verificados con stub; backend tests con fakes | Probar FastAPI real, ownership por recurso, token expirado, TLS/CORS; el login no es sesion HttpOnly |
| [#14](https://github.com/FerLpz55/PayPalAIHackathon-/issues/14) Generacion IA | Propuesta validada, missing info continuable, errores comprensibles con dobles | Abierta | Draft/error/retry visibles; stub ejercito 503 y retry 200; suite backend usa fakes | Credenciales/proveedor de prueba, generacion real y contrato customer-auth para aclaraciones |
| [#15](https://github.com/FerLpz55/PayPalAIHackathon-/issues/15) Revision/aprobacion quote | Ver descripcion/partidas/total/estado reales; completar datos y aprobar; carga/error/recarga | Cerrada | Parser y estados corregidos; stub y DEMO ejercitados | Contrato API+DB, aprobacion y persistencia real; issue ya figura cerrada remotamente |
| [#16](https://github.com/FerLpz55/PayPalAIHackathon-/issues/16) Pedidos/dashboard | Datos persistidos, PATCH autorizado persistente, carga/vacio/error sin mezcla | Cerrada | Paginacion, GET detail, payments y PATCH comprobados con stub; DEMO separada | Verificar autorizacion/transiciones/persistencia contra FastAPI/PostgreSQL |
| [#17](https://github.com/FerLpz55/PayPalAIHackathon-/issues/17) Pagos verificados | Importe/moneda calculados por server, duplicados/saldo controlados, retry probado | Abierta | Contratos y reglas backend; suite fake-backed pasa | PayPal Sandbox, carreras/idempotencia/persistencia y recuperacion operativa |
| [#18](https://github.com/FerLpz55/PayPalAIHackathon-/issues/18) Checkout | Pago Sandbox, retorno, confirmacion server-side, cancelar/error/reintentar | Abierta | Checkout consulta/captura por API en fuente; gate terminal probado con stub | Ejecutar sandbox completo con DB/API; ningun pago real se hizo |
| [#19](https://github.com/FerLpz55/PayPalAIHackathon-/issues/19) Recorrido E2E | Request->quote IA->approve->Sandbox verificado por backend; persistencia y errores; documentacion | Abierta | DEMO y stubs cubren flujos parciales; README e informes actualizados | E2E continuo API+DB+IA+Sandbox y persistencia tras recarga |
| [#20](https://github.com/FerLpz55/PayPalAIHackathon-/issues/20) Navegacion/tracking | Recuperacion tras navegar/recargar, aislamiento, pago confirmado por backend | Cerrada | Scope por ID/token, estados y pagos mapeados; stubs/DEMO | Sesion nueva, ownership y pagos reales en API/DB |
| [#21](https://github.com/FerLpz55/PayPalAIHackathon-/issues/21) A11y/responsive | Flujo con teclado, acciones visibles movil/escritorio, errores accesibles | Cerrada | Chromium puntual en 320/390/768/1280; lint/build | Cobertura total, browsers/dispositivos, teclado/AT; no es auditoria/certificacion |
| [#22](https://github.com/FerLpz55/PayPalAIHackathon-/issues/22) DEMO/documentacion | Marcar simulaciones; README y dependencias; lint/build o bloqueo documentado | Cerrada | DEMO sin API, copy Demo, README; lint y build pasan; bloqueo Vitest documentado | Revisar criterios remotos completos y desplegar; no se proclama REAL operativo |
| [#23](https://github.com/FerLpz55/PayPalAIHackathon-/issues/23) OWASP | Matriz A01-A10, hallazgos criticos, pruebas y limitaciones sin secretos | Abierta | Restricciones y riesgos documentados | Falta matriz OWASP y verificacion de seguridad completa; no declarar conformidad |
| #24 PR | Mejora a11y/responsive (no issue) | Cerrado y fusionado | PR oficial consultado; cambios previos ya en main | No es issue; esta iteracion no lo modifica |
| #25 PR | Separacion DEMO/REAL (no issue) | Cerrado y fusionado | PR oficial consultado; cambios previos ya en main | No es issue; esta iteracion no lo modifica |
| #26 PR | Dashboard y gestion de ordenes (no issue) | Cerrado y fusionado | PR oficial consultado; cambios previos ya en main | No es issue; esta iteracion no lo modifica |
| [#27](https://github.com/FerLpz55/PayPalAIHackathon-/issues/27) Infra live | Supabase, IA y PayPal Sandbox conectados; quote y pago reales | Abierta | No se uso DB, IA, PayPal ni se leyeron credenciales | Provision/autorizar staging, comprobar schema/migracion, IA y Sandbox |
| [#28](https://github.com/FerLpz55/PayPalAIHackathon-/issues/28) Entrega Hackathon | README ejecutable, enlaces #19/#23, video demo y submission | Abierta | README y docs de setup/status/pruebas actualizados; README enlaza issues | Agregar evidencia OWASP, grabar video y completar submission/flujo integral |

### Issue nueva recomendada

**Dictado `en-US` en solicitud de cliente.** Criterios propuestos: registrar permiso y compatibilidad por navegador; iniciar/detener; concatenar al texto previo; estados accesibles; errores de denegación, falta de micrófono, red/servicio y silencio; pruebas solo con mock automatizado. Aclarar que el reconocedor nativo puede transmitir audio a un proveedor del navegador. No cambiar el idioma. No asignar número hasta crear la issue en GitHub.

Para cerrar cualquier issue, sustituir el criterio provisional por el body oficial, enlazar commit/PR, prueba reproducible, y separar resultado DEMO/mocks de API/DB/servicio real. No se cierra una integración externa con solo tests unitarios.

### Actualización de evidencia — Fase 7

- **#15 (criterio provisional):** Quote Review ya muestra las medidas inglesas reconocidas por el adaptador; la regresión se reprodujo antes del cambio y la vista se comprobó después con datos DEMO. El test Vitest está añadido, pero no ejecutado porque el runner no está disponible localmente. Falta verificación automatizada y REAL para afirmar cobertura completa.
- **#21 (criterio provisional):** revisión puntual de ocho rutas a 320 px y Request en 768/1280 px sin overflow de página; navegación móvil comprobada a 390 px. Sigue parcial: no cubre todos los estados/textos, dispositivos reales, Safari/Firefox ni tecnología asistiva.
- La evidencia y limitaciones de esta fase están en [Informe Fase 7](INFORME_CORRECCIONES_FRONTEND_FASE_7.md). Ninguna issue se cerró ni se obtuvo su criterio oficial.

### Autenticación de taller — evidencia Fase 8

En la Fase 8 se verificó el guard fail-closed antes de que existiera el login. En ese momento no se asignó a issue porque sus cuerpos no se habían consultado; el estado actual de criterios oficiales está en la tabla superior. Ver [Informe Fase 8](INFORME_VERIFICACION_AUTH_FRONTEND_FASE_8.md).

### Login de taller — evidencia Fase 9

La UI ya tiene acceso Basic en memoria, Sign out, bloqueo de datos REAL sin sesión y expiración al 401. Evidencia local solo con stub loopback; no valida FastAPI ni credenciales de despliegue. La asociación a criterios oficiales está en la tabla superior; no se cambió el estado de issue alguna. [Informe Fase 9](INFORME_IMPLEMENTACION_LOGIN_TALLER_FASE_9.md).

### Consulta oficial y estado de verificacion para publicacion

La API pública del repositorio permitió leer cuerpos y estados. #10–#13, #15–#16 y #20–#22 figuran cerradas; #14, #17–#19, #23, #27 y #28 abiertas. #24–#26 son PRs ya fusionados, no issues. No había PR abierto antes de publicar esta rama. El CLI `gh` tiene token inválido y el navegador está desconectado, por lo que aún no se puede crear el PR. No se alteró estado remoto de ninguna issue.

La suite backend revisada en esta publicacion obtuvo **314 passed**; el frontend obtuvo lint/build exitosos, pero Vitest no se ejecuto. La evidencia local no satisface criterios que exijan API, PostgreSQL o proveedores reales.
