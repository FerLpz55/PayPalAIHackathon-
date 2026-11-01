# TallerClaro backend

Monolito FastAPI organizado por capas. Esta entrega es la base estructural:
solo implementa `GET /api/health` (liveness), sin verificar servicios externos.

El [plan del backend](../docs/superpowers/plans/2026-10-31-fastapi-layers.md)
define la arquitectura y el alcance. El frontend usa mocks locales y todavía
no consume esta API. Cotizaciones, pedidos, pagos y sus integraciones están pendientes.

## Desarrollo

Desde `Backend/`, con Python 3.11 o superior:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn tallerclaro.main:app --app-dir src --reload
```

Documentación interactiva: http://127.0.0.1:8000/docs

En Windows PowerShell, activar con `.venv\Scripts\Activate.ps1`.

```bash
python -m pytest
```

Configuración mediante variables de entorno, por ejemplo
`TALLERCLARO_APP_NAME`. No incluir secretos en el código ni en variables VITE.

## Estructura actual

```text
Backend/
  pyproject.toml
  src/tallerclaro/
    main.py
    domain/
    application/
    infrastructure/
    bootstrap/settings.py
    presentation/http/
      routers/health.py
      schemas/health.py
  tests/api/test_health.py
```

`main.py` construye la aplicación; el router y esquema de salud son la única
operación HTTP. `settings.py` lee configuración del entorno. `domain`,
`application` e `infrastructure` son paquetes reservados para las capas acordadas,
sin lógica todavía. Los archivos `__init__.py` identifican paquetes Python.

## Límites de arquitectura acordados

- `domain`: Python puro; entidades, reglas e importes `Decimal`. Sin FastAPI,
  Pydantic, ORM ni SDK externos.
- `application`: casos de uso, DTO internos y puertos `typing.Protocol`.
  Depende del dominio; recibe implementaciones por constructor.
- `presentation/http`: routers, esquemas Pydantic, autorización HTTP y errores.
  Delega las operaciones a los casos de uso.
- `infrastructure`: repositorios y adaptadores de IA y PayPal que implementan
  los puertos. Convierte modelos externos a tipos internos.
- `bootstrap` y `main.py`: configuración y composición. `Depends` permanece
  en la frontera HTTP.

Las responsabilidades anteriores son reglas para las próximas implementaciones.
Crear subpaquetes de cotizaciones, pedidos, pagos, puertos y adaptadores cuando
contengan código real. Lo mismo aplica a migraciones, pruebas unitarias y de
integración, dependencias HTTP y manejadores de errores: no se crean placeholders.
La base de datos, ORM, migraciones, autenticación, reglas de precios y proveedores
se definirán antes de implementar los respectivos casos de uso.

La IA propone una estimación; las reglas del dominio validan el importe pagable.
El estado de pago se mantiene separado del avance del pedido. Un retorno desde
checkout no demuestra un pago; la confirmación debe verificarse en el servidor
y procesarse de forma idempotente.

Pruebas unitarias: dominio y aplicación sin servicios externos. Integración:
adaptadores y transacciones. API: contrato HTTP y sustitución de dependencias.
No se ha conectado el frontend ni modificado su contrato propuesto.
