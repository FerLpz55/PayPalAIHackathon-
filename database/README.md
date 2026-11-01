# Base de datos — PostgreSQL

Directorio central para el esquema SQL y los archivos relacionados con PostgreSQL
de TallerClaro. La elección del motor está confirmada; el esquema y la conexión
con FastAPI todavía no están implementados.

## Organización

Crear los archivos y subdirectorios cuando se implemente su contenido:

- `schema.sql`: script inicial de creación del esquema.
- `migrations/`: cambios incrementales posteriores al esquema inicial.
- `seeds/`: datos de ejemplo para desarrollo, sin información personal real.

La herramienta de migraciones y la forma de ejecutar estos scripts están
pendientes de definir. Mantener una única secuencia de cambios del esquema;
no duplicarla en el backend.

## Integración y configuración

Los repositorios y modelos de persistencia Python vivirán en
`Backend/src/tallerclaro/infrastructure/`. El dominio y los casos de uso
permanecen independientes de PostgreSQL y del ORM.

Proporcionar las credenciales mediante configuración local o variables de entorno.
No guardar contraseñas, cadenas de conexión reales, dumps, copias de seguridad
ni directorios de datos de PostgreSQL en Git. Las plantillas de configuración
deben contener únicamente valores ficticios.

Consultar el [plan del backend](../docs/superpowers/plans/2026-10-31-fastapi-layers.md)
para la arquitectura y el alcance actual.
