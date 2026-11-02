# Directrices de Desarrollo de TallerClaro

## 1. Gestores de Paquetes y Entornos
- **Frontend (`frontend/`)**: Usar exclusivamente **`pnpm`** (`pnpm run dev`, `pnpm run lint`, `pnpm run build`, `pnpm install`). Nunca usar `npm` o `yarn`.
- **Backend (`Backend/`)**: Python 3.14 con entorno virtual en `Backend/.venv`. Pruebas con `.venv/bin/pytest`.

## 2. Infraestructura y Servicios (VPS con Coolify)
- **Base de Datos (PostgreSQL)**: La base de datos reside / se desplegará en un **servidor VPS administrado con Coolify**.
  - El agente **nunca** debe intentar levantar contenedores Docker o servicios locales de PostgreSQL.
  - La conexión del backend se realiza vía variables de entorno (`.env`) apuntando a dicha instancia remota de Coolify.
- **Pruebas de Backend**: Ejecutar siempre las pruebas en memoria existentes (`Backend/tests/`), las cuales usan dobles/fakes y no requieren conexión de red a la base de datos remota.
- **PayPal**: La integración de PayPal Sandbox se gestionará con sus credenciales de prueba; no simular pagos confirmados por servidor sin la API real.

## 3. Arquitectura del Backend
- El backend sigue una **arquitectura sencilla por capas (layered monolith)**:
  - `presentation/`: Endpoints HTTP con FastAPI y esquemas Pydantic.
  - `application/`: Casos de uso y orquestación.
  - `domain/`: Entidades puras y reglas de negocio (sin dependencias de frameworks).
  - `infrastructure/`: Repositorios y clientes externos (base de datos, IA, PayPal).
  - `bootstrap/`: Configuración y composición.
- No etiquetar esta arquitectura como "hexagonal" ni sobre-complejizar la nomenclatura técnica.

