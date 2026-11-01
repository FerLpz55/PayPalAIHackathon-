# TallerClaro: base monolítica por capas

## Objetivo

Preparar el backend FastAPI con las capas acordadas, sin anticipar decisiones
de persistencia o integrar proveedores todavía. Referencia de producto:
`REQUIREMENTS.md`; contrato propuesto: `frontend/docs/API_CONTRACT.md`.

## Entrega actual

- [x] Crear paquetes de dominio, aplicación, presentación, infraestructura y composición.
- [x] Configurar empaquetado Python, dependencias y entorno de desarrollo.
- [x] Exponer `GET /api/health` con respuesta `200 {"status": "ok"}`.
- [x] Documentar las dependencias permitidas y el arranque local.
- [x] Verificar la prueba HTTP sin servicios externos (1 prueba aprobada).

## Estructura mínima y documentación

Se conservan los paquetes principales `domain`, `application`, `presentation`,
`infrastructure` y `bootstrap`. Solo presentación y composición contienen
código funcional en esta entrega. Los subpaquetes de negocio, puertos, DTO,
adaptadores, migraciones y suites unitarias/de integración se crearán con su
primera implementación; se retiraron los placeholders vacíos y los módulos
de dependencias HTTP y errores que solo contenían comentarios.

Este plan define la arquitectura y el alcance del backend. `Backend/README.md`
documenta estructura y ejecución; el README general resume el estado del proyecto.
`frontend/docs/API_CONTRACT.md` sigue siendo una propuesta de operaciones futuras.

## Reglas

Dominio en Python puro e importes Decimal. Aplicación depende del dominio y
declara puertos Protocol, con inyección por constructor. FastAPI y Pydantic
se usan en HTTP y configuración; el ORM y SDK externos quedan en infraestructura.
La composición es el punto donde se conectan las implementaciones.

## Continuación pendiente

Elegir base de datos y política de precios antes de desarrollar persistencia
y generación de cotizaciones. Luego implementar una operación completa por vez:
generar y consultar cotización, aprobar y crear pedido, iniciar y verificar pago,
consultar y actualizar pedido con autorización. Definir política de acceso del
cliente sin introducir cuentas fuera del alcance del MVP.

Antes de pagos, definir moneda, redondeo, anticipos y vigencia. Mantener pago y
producción separados y procesar confirmaciones verificadas de forma idempotente.
Las rutas de negocio aún no existen; no devolver éxitos simulados desde esta base.

## Validación

Prueba HTTP de liveness, comprobación de sintaxis y revisión del diff.
En las siguientes entregas: pruebas unitarias del negocio, integración con la
base elegida y pruebas de contrato HTTP; incluir rechazo de importes manipulados,
confirmaciones repetidas y transiciones de pedido inválidas.
