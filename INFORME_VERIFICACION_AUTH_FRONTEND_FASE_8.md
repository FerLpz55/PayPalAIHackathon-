# Verificación de autenticación frontend — Fase 8

Fecha: 9 de noviembre de 2026. Inspección y ejecución local del modo REAL con URL loopback ficticia. Sin credenciales, backend, red externa ni cambios de código.

## Estado encontrado

- `frontend/src/services/http.js` no contiene un usuario/contraseña de fallback. `workshopCredentials` se lee de `sessionStorage`; el único uso actual encontrado es formar `Authorization: Basic ...` para rutas marcadas de taller.
- Cuando una llamada de taller no tiene credenciales, `apiRequest()` lanza `ApiError` 401 antes de `fetch`, con el mensaje `Workshop sign-in is not configured in this browser. No request was sent.`
- No encontré un login, formulario, acción ni setter que establezca `workshopCredentials`. Por tanto, el cliente ya falla cerrado, pero la sesión de taller no puede iniciarse desde la interfaz actual.

## Ejecución REAL local aislada

Vite 8.3.5 se inició en `127.0.0.1:5173` con `VITE_APP_MODE=real` y una base ficticia `http://127.0.0.1:9`. No existía servicio en ese puerto. En Dashboard, la interfaz presentó alertas para el resumen y para las órdenes; explicó que no se envió ninguna solicitud y que no mostraría órdenes de ejemplo como órdenes reales. “Retry connection” mantuvo ese comportamiento.

El listado de red filtrado por `/api/` quedó vacío. Esto confirma el guard de credenciales en el cliente; no prueba autenticación contra FastAPI, CORS ni autorización del servidor. No se envió contraseña, Basic, customer token ni otro secreto. El servidor Vite se detuvo al acabar.

## Conclusión y criterio de implementación

La credencial Basic fija del frontend está ausente en el árbol actual. La integración REAL de taller sigue incompleta por falta de un mecanismo de inicio de sesión y gestión de sesión. Antes de implementarlo hace falta decidir si el cliente conservará Basic en memoria/sesión bajo HTTPS o si se utilizará un BFF/sesión de servidor, además de expiración, cierre de sesión y rotación. No se inventó endpoint ni flujo durante esta fase.

## Cambios y límites

- No se modificó código, `.env`, configuración, GitHub ni infraestructura.
- Ninguna API, DB, proveedor de IA, Channel3 o PayPal fue contactado.
- Evidencia del navegador: mensaje visible y ausencia de requests `/api/`. Issues no se cerraron.
- Siguiente paso: decisión de autenticación y luego diseño de UI/tests local; solo después probar el mecanismo con servidor de prueba autorizado.
