# Informe de correcciones frontend - Fase 4

Fecha: 9 de noviembre de 2026. Alcance: conservar el texto del cliente cuando falla el envio de informacion adicional en Quote Review. Prueba con Vite y servidor HTTP ficticio limitado a 127.0.0.1; no se conecto FastAPI, PostgreSQL, IA ni servicios externos.

## Correccion

En frontend/src/pages/customer/QuoteReviewPage.jsx, el campo additionalInfo se limpia solo cuando mutate() indica exito. Si devuelve false tras un fallo, el texto permanece disponible para corregir o reintentar. El estado needs_information ahora presenta el arreglo missing_info del backend como una lista accesible, en lugar de dejar la solicitud en un mensaje generico. Las sugerencias de catalogo se hidratan al cargar la quote, se reinician al cambiar su ID y las respuestas de busqueda de una quote anterior se descartan.

## Reproduccion y verificacion

- Antes del cambio: con sesion ficticia, quote TC-101 en needs_information y sin credencial de taller, escribir "Use FSC-certified oak and a matte finish." y enviar produjo el error visible "Workshop sign-in is not configured in this browser. No request was sent."; el campo quedo vacio. La unica llamada API fue el GET inicial al stub.
- Despues, error simulado: el stub recibio POST /api/quotes/101/generate con Basic ficticio y respondio 503. La alerta "Fictional workshop authentication/service unavailable" quedo visible y el texto permanecio en el campo.
- Despues, exito simulado: un POST posterior respondio 200 y el GET devolvio pending_review con un item y total ficticios. La UI refresco la cotizacion y limpio el campo.
- Stub y app usaron loopback; solo datos y credenciales ficticios. No se activo microfono, no se envio informacion real y no se aprobo ni pago una cotizacion.
- Aislamiento de sugerencias: quote 101 devolvio Product only for quote 101 y quote 102 devolvio una lista vacia. Antes, tras buscar para 101 y cambiar query ID a 102 sin desmontar la pantalla, el producto de 101 seguia visible. Despues, las sugerencias iniciales de 101 se cargaron, al cambiar a 102 desaparecieron y se mostro el estado sin productos. Tambien se disparo una busqueda de catalogo de 101 y se cambio a 102 antes de que respondiera; la respuesta retrasada no repoblo el catalogo de 102.

## Limite del contrato

La vista cliente sigue enviando los detalles al endpoint POST /api/quotes/{id}/generate, que exige autenticacion Basic de taller. Sin esa sesion, el navegador bloquea la peticion explicitamente. La correccion conserva el texto y muestra el error, pero no resuelve como debe enviar aclaraciones un cliente: falta definir/implementar el contrato autorizado. No se invento endpoint ni se cambio autenticacion.

## Verificaciones

- Reproduccion interactiva antes de editar y comprobacion posterior del 503 y 200 con Playwright y servidor ficticio local.
- Quote ficticia con missing_info = ["Specify preferred wood species", "Confirm whether assembly is required"]: antes solo aparecia el estado generico; despues ambas solicitudes se mostraron como elementos de una lista semantica bajo "Information requested by the workshop".
- Cambio de quote 101 -> 102, estado inicial de sugerencias y busqueda retrasada: comprobado con Playwright; Chromium no reporto errores de consola.
- `node node_modules/eslint/bin/eslint.js src` (desde frontend): exit code 0.
- Build DEMO con `VITE_APP_MODE=demo`, `VITE_API_BASE_URL` vacia y `node node_modules/vite/bin/vite.js build`: Vite 8.3.5, 61 modulos, exit code 0.
- Vitest no esta disponible en frontend/node_modules; no se instalaron dependencias. La prueba de navegador es manual, no automatizacion persistente.
