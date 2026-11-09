# Implementación del login de taller — Fase 9

Fecha: 9 de noviembre de 2026. El usuario eligió Basic Auth en memoria por ahora. Alcance: completar el acceso de taller en frontend usando las rutas Basic ya existentes, sin crear endpoint de login, modificar backend o emplear credenciales reales.

## Implementación

- Topbar ofrece Sign in / Sign out en modo REAL. DEMO conserva su perfil y datos locales sin flujo de login.
- El diálogo recoge username/password y valida el acceso con la petición de solo lectura ya existente `GET /api/orders?limit=1&offset=0`.
- El header Basic codificado se conserva solo en una variable de módulo en memoria. No se guarda en `sessionStorage` ni `localStorage`; al recargar la pestaña se requiere entrar otra vez.
- Se permite enviar Basic solo por HTTPS, con HTTP habilitado exclusivamente para loopback de desarrollo.
- Sin credenciales, el cliente no hace `fetch` a rutas de taller y muestra una pantalla que requiere acceso. No se muestran datos DEMO en REAL.
- Un `401` borra Basic en memoria, emite el evento de sesión perdida y oculta los datos de taller; Sign out hace lo mismo localmente.
- Las credenciales no se verifican con un endpoint nuevo ni se incluyó ninguna credencial fija.

## Prueba funcional local

Vite REAL en `127.0.0.1:5173` apuntó a un stub HTTP ficticio en `127.0.0.1:8001`. Se usaron unicamente credenciales ficticias; el stub no registro sus valores. El stub comprobó si el header coincidía; nunca registró su valor. Se eliminó el archivo temporal y se detuvieron ambos procesos.

- Antes del login: pantalla “Sign in to your workshop”, sin requests `/api/`.
- Credenciales ficticias incorrectas: GET protegido devuelve 401, el diálogo muestra el mensaje del backend y el usuario sigue sin sesión. La consola del navegador registra el status HTTP 401 esperado; no hubo error React.
- Credenciales ficticias válidas: GET protegido devuelve 200; el stub confirma `basic-match=true`; aparece Sign out y la app solicita los recursos existentes con Basic.
- El resumen ficticio 503 se muestra como “unavailable” con valores `—`; no se convierte en cero.
- Al forzar un 401 después de iniciar sesión, la app vuelve al estado de acceso, deja de mostrar el pedido ficticio y la credencial en memoria queda vacía.
- Sign out manual también oculta los datos y no genera otra solicitud al API.
- Se llamó `location.reload()` tras autenticar: la sesión no sobrevive a la recarga y el gate vuelve a aparecer. `sessionStorage` y `localStorage` no contienen `workshopCredentials`.
- A 320 px el diálogo mide 280 px, no desborda la página y enfoca el campo de usuario.

## Verificación técnica

- ESLint `frontend/node_modules/.bin/eslint.cmd src`: exit code 0.
- Build `frontend/node_modules/.bin/vite.cmd build`: Vite 8.3.5, 62 módulos transformados, exit code 0.
- `git diff --check` de los archivos de esta fase: exit code 0.
- Vitest no disponible: `frontend/node_modules/vitest/vitest.mjs` y `.bin/vitest.cmd` no existen. No se instalaron dependencias.
- No se conectó FastAPI, PostgreSQL, Supabase, IA, Channel3, PayPal ni otro servicio externo. La prueba loopback demuestra el cableado del cliente y el manejo de estados, no la aceptación por el backend real.

## Riesgo y trabajo restante

Basic queda en memoria mientras la sesión está abierta y puede ser leído por JavaScript que se ejecute en el origen. El HTTPS obligatorio protege el tránsito, pero este patrón no equivale a una cookie HttpOnly/BFF. El usuario eligió este esquema transitorio; backend, TLS/CORS de despliegue, rotación/expiración de password y control de roles siguen pendientes de verificación. Para probar acceso real se requiere una URL backend de staging HTTPS y una cuenta de taller de prueba autorizada; no usar producción.

## Archivos modificados

- `frontend/src/App.jsx`
- `frontend/src/components/layout/Topbar.jsx`
- `frontend/src/components/layout/WorkshopSignInDialog.jsx`
- `frontend/src/hooks/useDemoData.js`
- `frontend/src/services/apiClient.js`
- `frontend/src/services/http.js`
- `frontend/src/services/sessionStore.js`
- `frontend/src/services/__tests__/sessionStore.test.js`
- `frontend/src/styles/app.css`
- `INFORME_IMPLEMENTACION_LOGIN_TALLER_FASE_9.md`
- `MATRIZ_FUNCIONAL_FRONTEND_BACKEND.md`
- `MATRIZ_ISSUES_Y_CRITERIOS_ACEPTACION.md`
- `INFORME_PRUEBAS_E2E.md`
- `PENDIENTES_INFRAESTRUCTURA_Y_CREDENCIALES.md`
- `PLAN_MAESTRO_INTEGRACION_MVP.md`

No se cerró ninguna issue ni se alteraron cambios previos del repositorio.
