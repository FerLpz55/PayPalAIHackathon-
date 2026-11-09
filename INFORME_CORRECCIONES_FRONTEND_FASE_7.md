# Informe de correcciones frontend - Fase 7

Fecha: 9 de noviembre de 2026. Alcance: revisar reflow local en pantallas clave y corregir el parser de medidas para descripciones en inglés. Sin cambios de infraestructura ni llamadas a servicios externos.

## Estado de partida y preservación

- El árbol ya contenía cambios locales de fases anteriores y documentos sin seguimiento; todos se conservaron.
- Git rechazó por propiedad distinta al invocarse normalmente. Se consultó solo con `git -c safe.directory=... status/diff --check` para esta verificación; no se cambió la configuración global/local.
- Vite se inició directamente desde `frontend/node_modules/.bin` en `127.0.0.1:5173`, con `VITE_APP_MODE=demo` temporal en el proceso. No se leyó ni modificó `.env`.
- La skill Impeccable no pudo cargar contexto: el engine no está instalado y requiere red y permiso de escritura fuera del workspace. Se leyeron directamente `AGENTS.md` y la guía de revisión; no se instaló el engine.

## Defecto reproducido y corrección

Una solicitud DEMO ficticia con `Demo desk, 120 cm wide, oak, simple legs` aparecía en Quote Review con dimensiones vacías (`- wide · - tall · - deep`). `extractMeasurements()` solo reconocía `ancho`, `alto` y `profundidad`, aunque la interfaz y el dictado acordado usan inglés `en-US`.

Se extendieron las expresiones del adaptador para reconocer `wide`, `tall`/`high` y `deep`, manteniendo el vocabulario español. Se añadió una prueba Vitest para `120 cm wide, 75 cm tall, and 55 cm deep` junto a la prueba española existente.

La verificación en el navegador DEMO después del cambio mostró `120 cm wide · 75 cm tall · 55 cm deep`. La misma cotización y sus dimensiones siguieron visibles después de recargar la ruta. La importación dinámica del adaptador confirmó tanto la frase inglesa como la española. El defecto inicial y la solución se observaron en el navegador con datos ficticios.

## Comprobación responsive y de navegación

En Chromium, la anchura del documento y los elementos de `main` se revisaron a 320, 390, 768 y 1280 CSS px:

- A 320 px: Request, Quote Review, Tracking, Quotes, Orders, Order Detail, Receipts y Accounting quedaron dentro del viewport, sin desbordamiento horizontal de página ni elementos de contenido fuera de sus límites.
- A 390 px: el menú móvil abrió; el enlace Orders navegó a `#/orders` y cerró el menú. Documento y contenido midieron 380 px frente al viewport de 390 px (el área restante corresponde a la barra vertical).
- A 768 px y 1280 px: Request permaneció dentro del viewport sin desbordamiento horizontal.
- Orders mantiene sus variantes compactas; no se detectó scroll horizontal de página en estas rutas.

Estas son comprobaciones de navegador en Chromium, no pruebas en dispositivos físicos, Safari, Firefox ni lectores de pantalla. No se activó el micrófono.

## Verificación local

- ESLint: `frontend/node_modules/.bin/eslint.cmd src` -> exit code 0.
- Build: `frontend/node_modules/.bin/vite.cmd build` -> Vite 8.3.5, 61 módulos transformados, exit code 0.
- `git diff --check` de los dos archivos de código editados -> exit code 0, sin salida.
- Vitest no se pudo ejecutar: `frontend/node_modules/.bin/vitest.cmd` no existe. `pnpm --dir frontend ...` falló al abrir el lock de la store con `ERR_PNPM_STORE_DIR_OPEN_OPERATION_LOCK`; no se instalaron dependencias ni se alteró configuración. La aserción de regresión quedó añadida, pero requiere habilitar el runner ya declarado para ejecutarse.

## Archivos modificados en esta fase

- `frontend/src/services/adapters.js`
- `frontend/src/services/__tests__/adapters.test.js`
- `INFORME_CORRECCIONES_FRONTEND_FASE_7.md`
- `MATRIZ_FUNCIONAL_FRONTEND_BACKEND.md`
- `MATRIZ_ISSUES_Y_CRITERIOS_ACEPTACION.md`
- `INFORME_PRUEBAS_E2E.md`
- `PLAN_MAESTRO_INTEGRACION_MVP.md`

No se modificó backend, CSS, configuración ni credenciales. DEMO usó localStorage en este navegador; sus datos de prueba se retiraron al finalizar. No hubo tráfico a `/api/`, PostgreSQL, IA, Channel3 ni PayPal.

## Pendientes

- Ejecutar el test Vitest añadido cuando el runner local declarado esté disponible, sin instalarlo en esta fase.
- Mantener separado este resultado DEMO de cualquier comprobación REAL: no verifica AI, API, PostgreSQL ni persistencia de servidor.
- Issues #15 y #21 conservan estado provisional/parcial; no se cerró ninguna issue ni se consultó GitHub.
