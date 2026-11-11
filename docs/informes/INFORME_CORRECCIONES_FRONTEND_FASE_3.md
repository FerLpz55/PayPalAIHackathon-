# Informe de correcciones frontend — Fase 3

Fecha: 9 de noviembre de 2026. Alcance: conectar la vista de pedidos al contrato de paginación existente. Se utilizó un stub HTTP local con datos ficticios; no se conectó FastAPI, PostgreSQL ni ningún servicio externo.

## Cambio

- `apiClient.listOrdersPage({limit, offset})` valida los parámetros, envía `GET /api/orders?limit=…&offset=…` con autenticación de taller y adapta `{orders,total,limit,offset}`. DEMO pagina los fixtures locales sin cambiar su almacenamiento.
- `OrdersPage` muestra controles accesibles de página anterior/siguiente, total y rango; presenta carga y errores de la consulta de página. La búsqueda y los filtros se limitan explícitamente a la página visible. Al borrar el último registro de una página, vuelve a la página válida más cercana.
- `listOrders()` conserva el contrato interno existente de devolver un arreglo y obtiene la primera página a través del nuevo método.

## Evidencia

- Chromium en modo REAL con URL local `http://127.0.0.1:8001` y un servidor ficticio que exigió el Basic inventado `dGVzdDp0ZXN0` y devolvió 45 órdenes sintéticas.
- La interfaz mostró las páginas 1–20, 21–40 y 41–45. “Next” quedó deshabilitado al llegar al final; “Previous” regresó de la página 3 a la 2.
- Network registró GET con `limit=20&offset=0`, después `offset=20`, `offset=40` y regreso a `offset=20`. El total mostrado permaneció en 45.
- El stub y Vite escucharon solo en `127.0.0.1`; se cerraron al acabar. Consola Chromium sin errores. Esta prueba demuestra cableado frontend↔stub, no compatibilidad con FastAPI real ni persistencia.
- En una segunda ejecución independiente, DEMO mostró sus ocho pedidos de `localStorage` y el summary local con métricas 8/3/5/0; no mostró controles de paginación (el total es menor que el tamaño de página) ni hizo solicitudes `/api/`.
- `node node_modules\\eslint\\bin\\eslint.js src` — exit 0.
- Build DEMO con Vite 8.3.5 — exitoso, 61 módulos transformados.

- Dashboard consulta GET /api/accounting/summary. Stub local devolvio conteos 33/12/8/4 y la UI los mostro tal cual; un 503 ficticio produjo alerta, metricas desconocidas, reintento y mantuvo el listado visible. El reintento volvio a consultar el summary.

- Order Detail consulto GET /api/orders/1001 y mostro importes/pagos del cuerpo recibido; PATCH /api/orders/1001 envio {"status":"in_progress"}, reflejo el estado y recargo el detalle. Prueba con stub local, no FastAPI ni DB reales.

## Pendiente

- Vitest no se ejecutó porque el paquete no está disponible en `frontend/node_modules`; no se instalaron dependencias. La respuesta paginada real del backend y permisos Basic requieren una API de prueba configurada.
- Búsqueda y filtro se aplican únicamente a la página cargada porque el endpoint actual solo define `limit`/`offset`, no filtros server-side.
- Quotes sigue derivando su lista de la pagina inicial de pedidos porque no existe endpoint de listado de cotizaciones. Dashboard usa el summary global; persistencia y contrato real siguen pendientes.

No se tocaron credenciales, `.env`, manifiestos, locks, backend ni base de datos. Ninguna issue se cerró. Ver [matriz funcional](MATRIZ_FUNCIONAL_FRONTEND_BACKEND.md), [pruebas E2E](INFORME_PRUEBAS_E2E.md) y [plan maestro](PLAN_MAESTRO_INTEGRACION_MVP.md).
