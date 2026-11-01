# Plan: script PostgreSQL de TallerClaro

## 1. Objetivo, alcance y decisiones propuestas

Crear manualmente `database/schema.sql` a partir del diagrama aportado: seis
tablas, integridad referencial, importes exactos, índices y marcas de tiempo.
El backend sigue siendo un monolito FastAPI por capas. Esta tarea no conecta
FastAPI, implementa pagos ni agrega autenticación, recibos, inventario o cuentas.

Este documento es un plan. El esquema inicial ya fue implementado en
`database/schema.sql`, con semillas en `database/seeds/demo.sql` y pruebas en
`database/tests/schema_test.sql`. Las pruebas locales quedan pendientes hasta
contar con un servidor PostgreSQL disponible.

Supuestos propuestos, pendientes de tus respuestas:

- Conservar las seis entidades y permitir los ajustes documentados abajo.
- PostgreSQL 18, base `tallerclaro`, esquema dedicado `tallerclaro`.
- MXN, dos decimales monetarios y anticipo del 50 % para el ejemplo del MVP.
  El porcentaje es una política del backend; no se fija como CHECK del esquema.
- Ejecución local con `psql`. El SQL de esquema será SQL puro y también podrá
  ejecutarse desde DataGrip o pgAdmin seleccionando la base correcta.
- Un pedido pertenece al mismo carpintero que su cotización. Cada cotización
  puede originar como máximo un pedido. Cada registro de pago corresponde a un
  intento de checkout con una sola captura completa de PayPal.
- Sin reembolsos ni capturas parciales por intento en esta versión. Nuevos
  intentos de pago crean filas nuevas. Estos casos requerirían ampliar el modelo.

## 2. Archivos que crearás

```text
database/
  README.md                 instrucciones y decisiones del esquema
  .gitignore                ya existe: datos locales y respaldos excluidos
  schema.sql                única definición inicial del esquema
  seeds/demo.sql            ejemplos ficticios, opcionales
  tests/schema_test.sql     pruebas SQL que revierten sus datos al finalizar
```

No crear un segundo esquema en `Backend/`, ni directorios de migraciones vacíos.
Tras aplicar y versionar esta primera versión, los cambios irán en migraciones
numeradas; la primera migración futura partirá de esta base, sin duplicarla.
No editar el script inicial para actualizar bases ya utilizadas.

## 3. Convenciones que aplicarás

- Tablas y columnas en español, singular, minúsculas y `snake_case`, sin comillas.
- PK: `bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY`. Las FK serán `bigint`.
- Textos: `text`. `NOT NULL` salvo las excepciones indicadas en la tabla siguiente.
  Añadir `CHECK (btrim(campo) <> '')` a textos obligatorios.
- Importes: `numeric(14,2)`; cantidades: `numeric(12,3)`. Nada de `float` o `money`.
  Excluir `NaN` además de comprobar signo; los límites de precisión excluyen infinito.
- `moneda`: `text NOT NULL DEFAULT 'MXN' CHECK (moneda = 'MXN')` en cotización,
  pedido y pago mientras el MVP sea de una sola moneda. Si eliges USD, sustituir
  MXN en todos los lugares; no permitir monedas diferentes por accidente.
- Fechas de eventos: `timestamptz`; fecha estimada: `date`.
  `fecha_creacion DEFAULT now()` y `ultima_actualizacion DEFAULT now()`.
- Estados: `text` con CHECK nombrado, sin ENUM PostgreSQL para facilitar cambios.
- Nombres de restricciones: `pk_<tabla>`, `fk_<tabla>_<referencia>`,
  `uq_<tabla>_<campo>`, `ck_<tabla>_<regla>`; índices: `ix_<tabla>_<columnas>`.
- FK con `ON DELETE RESTRICT ON UPDATE RESTRICT`: no eliminar historial en cascada.
  Los identificadores son inmutables para el uso normal.
- Usar siempre nombres calificados, por ejemplo `tallerclaro.pedido`.

## 4. Diseño tabla por tabla

Todos los campos del diagrama se conservan salvo las normalizaciones y adiciones
explicadas. Todos son obligatorios excepto donde se indique `NULL`.

### 4.1. cliente

| Campo | Definición |
|---|---|
| id_cliente | PK identity |
| nombre | text no vacío |
| correo | text no vacío, almacenado con trim y en minúsculas |
| telefono | text NULL; si existe, no vacío; conservar prefijo y ceros |
| fecha_creacion | timestamptz DEFAULT now() |
| ultima_actualizacion | timestamptz DEFAULT now() |

No hacer correo único: el requisito no establece que un correo identifique a
una persona ni existe registro de cuentas. Validar formato en FastAPI; el
CHECK solo exige `correo = lower(btrim(correo))` y que no esté vacío.

### 4.2. carpintero

| Campo | Definición |
|---|---|
| id_carpintero | PK identity |
| nombre, nombre_taller | text no vacío |
| correo | text no vacío; normaliza `email` del diagrama al nombre `correo` |
| telefono | text NULL, no vacío si existe |
| fecha_creacion | timestamptz DEFAULT now() |

Normalizar correo como en cliente. No introducir contraseña ni asumir que este
registro constituye una cuenta autenticada. No hacer `nombre_taller` único.

### 4.3. cotizacion

| Campo | Definición |
|---|---|
| id_cotizacion | PK identity |
| id_cliente | FK a cliente |
| id_carpintero | FK a carpintero |
| solicitud | text no vacío: petición original |
| descripcion | text NULL mientras falte información; no vacío si existe |
| monto_total | numeric(14,2) NULL en borradores; finito y >= 0 si existe |
| estado | text DEFAULT 'draft' |
| moneda | MXN según convención |
| fecha_creacion, ultima_actualizacion | timestamptz DEFAULT now() |

CHECK de estado: `draft`, `needs_information`, `pending_review`, `approved`,
`rejected`, coherente con el contrato propuesto del frontend.
Para `pending_review` y `approved`, exigir descripción y `monto_total > 0`
en un CHECK adicional. Un borrador puede no tener detalles; una cotización
pagable debe tener al menos uno, regla a comprobar en el caso de uso.

Añadir `UNIQUE (id_cotizacion, id_carpintero)`: será la clave referenciada
por la FK compuesta del pedido para asegurar que el carpintero coincide.

### 4.4. detalle_cotizacion

| Campo | Definición |
|---|---|
| id_detalle | PK identity |
| id_cotizacion | FK a cotizacion |
| tipo | text CHECK IN ('material', 'labor', 'other') |
| descripcion, unidad | text no vacío |
| cantidad | numeric(12,3), finita y > 0 |
| precio_unitario | numeric(14,2), finito y >= 0 |
| importe | numeric(14,2) GENERATED ALWAYS AS (round(cantidad * precio_unitario, 2)) STORED |

La aplicación no envía `importe` en INSERT o UPDATE. Se redondea cada renglón
a dos decimales y luego se suman los renglones. El total de cabecera no puede
ser una columna generada porque depende de filas de otra tabla.

### 4.5. pedido

| Campo | Definición |
|---|---|
| id_pedido | PK identity |
| id_cotizacion | bigint UNIQUE: una cotización, como máximo un pedido |
| id_carpintero | bigint obligatorio |
| codigo | text UNIQUE no vacío; generado por backend, nunca con MAX(id)+1 |
| monto_total | numeric(14,2), finito y > 0; copia del precio aprobado |
| monto_anticipo | numeric(14,2), finito, entre 0 y monto_total |
| moneda | adición: moneda del precio acordado |
| estado | text DEFAULT 'pending'; CHECK IN ('pending','paid','in_progress','delivered') |
| fecha_creacion | timestamptz DEFAULT now() |
| ultima_actualizacion | adición: timestamptz DEFAULT now() |
| fecha_entrega_estimada | date NULL |

Crear FK `(id_cotizacion, id_carpintero)` a
`cotizacion(id_cotizacion, id_carpintero)`. No agregar otra FK simple redundante
de pedido a cotización ni otra a carpintero: la compuesta ya valida ambos.

`estado` conserva los cuatro valores exigidos por el proyecto. No añadir los
estados ilustrativos del frontend como `quote_sent`. El estado de pago se
derivará de pagos completados, no de la columna `estado` de pedido.

### 4.6. pago

| Campo | Definición |
|---|---|
| id_pago | PK identity |
| id_pedido | FK a pedido |
| tipo | text CHECK IN ('deposit','balance') |
| monto | numeric(14,2), finito y > 0 |
| moneda | MXN según convención |
| estado | text DEFAULT 'pending'; CHECK IN ('pending','completed','failed','cancelled') |
| paypal_order_id | text NULL; UNIQUE; no vacío si existe |
| paypal_capture_id | adición: text NULL; UNIQUE; no vacío si existe |
| fecha_creacion | adición: timestamptz DEFAULT now() |
| ultima_actualizacion | adición: timestamptz DEFAULT now() |
| fecha_pago | timestamptz NULL; nunca DEFAULT now() |

El estado `completed` exige los dos identificadores de PayPal y `fecha_pago`.
Los demás estados exigen `paypal_capture_id IS NULL` y `fecha_pago IS NULL`.
`paypal_order_id` puede ser NULL antes de obtener respuesta del proveedor.
UNIQUE permite múltiples NULL, pero impide repetir identificadores reales.

No hacer `UNIQUE(id_pedido,tipo)`: impediría reintentar un pago fallido.
Los webhooks repetidos de una misma captura actualizan o consultan el mismo
intento, sin crear otro ingreso. Verificar la autenticidad sigue siendo
responsabilidad del backend: una fila SQL no demuestra un cobro real.

## 5. Orden exacto para escribir schema.sql

1. Encabezado con propósito, versión objetivo y advertencia: solo base nueva.
2. `BEGIN;`, seguido de `SET LOCAL TIME ZONE 'UTC';`.
3. `CREATE SCHEMA tallerclaro;` sin `IF NOT EXISTS`.
4. `REVOKE ALL ON SCHEMA tallerclaro FROM PUBLIC;`.
5. Crear, en orden: cliente, carpintero, cotizacion, detalle_cotizacion, pedido, pago.
6. Incluir las PK, NOT NULL, CHECK, UNIQUE y FK del apartado 4.
7. Crear los índices indicados abajo.
8. Crear una función PL/pgSQL `tallerclaro.actualizar_timestamp()` que asigne
   `NEW.ultima_actualizacion := statement_timestamp(); RETURN NEW;`.
9. Crear un trigger `BEFORE UPDATE FOR EACH ROW` en cliente, cotizacion, pedido
   y pago que ejecute esa función. Usar función normal SECURITY INVOKER.
10. Añadir COMMENT ON TABLE y comentarios en importes, estados e IDs PayPal.
11. Terminar con `COMMIT;`. No incluir CREATE DATABASE, contraseñas, DROP,
    TRUNCATE, datos de ejemplo o comandos propios de psql dentro de schema.sql.

Si se vuelve a ejecutar el script sobre la misma base, debe fallar al crear el
esquema y revertir, sin borrar información ni ocultar diferencias de versión.

### Índices que crearás

- `cotizacion(id_cliente)`.
- `cotizacion(id_carpintero, fecha_creacion DESC)`.
- `detalle_cotizacion(id_cotizacion)`.
- `pedido(id_carpintero, fecha_creacion DESC)`.
- `pago(id_pedido)`.

Los índices de PK, UNIQUE de código, IDs PayPal e id_cotizacion del pedido
ya se crean con las restricciones: no duplicarlos. El índice único de
cotización `(id_cotizacion,id_carpintero)` respalda la referencia compuesta.
Agregar filtros por estado u otros índices después de medir consultas reales.

## 6. Reglas transaccionales que no resolverá el script inicial

Estas reglas son contrato de los futuros casos de uso FastAPI. El esquema
inicial no se debe presentar como si ya las garantizara por sí solo:

1. Crear/editar cotización: guardar cabecera y detalles en una transacción,
   recalcular el total desde los importes generados y actualizar la cabecera.
2. Aprobar: exigir al menos un detalle, precio validado y total coincidente;
   bloquear la cotización con `SELECT ... FOR UPDATE`.
3. Crear pedido: leer cotización aprobada bloqueada, copiar carpintero,
   moneda y total; calcular anticipo con Decimal y redondeo ROUND_HALF_UP;
   generar código desde UUID, por ejemplo `TC-` + UUID completo sin guiones.
4. Después de crear pedido, no modificar ni borrar la cotización aprobada ni
   sus detalles desde los casos de uso. Un cambio comercial será otra cotización.
5. Preparar pago: calcular importe desde anticipo o saldo persistido. No confiar
   en montos del navegador. No dejar una transacción abierta durante llamadas a PayPal.
6. Confirmar pago: tras verificar PayPal en servidor, bloquear primero el pedido
   y después su intento de pago, comprobar monto, moneda e IDs y actualizarlo.
   Si la captura ya está completada, devolver el resultado existente.
7. Todos los flujos que modifican pagos bloquean el mismo pedido para serializar
   confirmaciones. Impedir que la suma completada exceda el total; si el proveedor
   informa una anomalía real, no descartarla: requerirá conciliación antes de
   ampliar esta versión. No habilitar el cobro real con esta implementación MVP.
8. Derivar estado financiero como unpaid, partially_paid o paid según la suma
   completada. No mezclarlo con failed de un intento anterior. `paid` de pedido
   significa total liquidado; no representa el mero pago del anticipo.
9. Para delivered, exigir total liquidado. Para in_progress, aplicar la política
   de anticipo del negocio. El CHECK de estados solo restringe vocabulario,
   no valida transiciones ni pagos de otras tablas.

No usar CHECK con consultas a otras tablas ni sumar pagos mediante triggers
sin una estrategia de concurrencia. En esta entrega solo habrá triggers de fecha.

## 7. Cómo crear y ejecutar la base local

Requisitos: servidor PostgreSQL 18 iniciado y cliente psql disponible.
Ejecutar desde la raíz del repositorio; los nombres siguientes son ejemplos locales.

1. Entrar como administrador: `psql -h localhost -U postgres -d postgres -W`.
2. Crear propietario de desarrollo sin privilegios administrativos:
   `CREATE ROLE tallerclaro_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;`.
3. Dentro de psql, ejecutar `\password tallerclaro_owner`; introducir contraseña
   de forma interactiva. No escribirla en el SQL ni en una URL de conexión.
4. Crear base: `CREATE DATABASE tallerclaro OWNER tallerclaro_owner;`.
5. Salir con `\q`.
6. Aplicar el script:

```bash
psql -X -h localhost -U tallerclaro_owner -d tallerclaro -W -v ON_ERROR_STOP=1 -f database/schema.sql
```

El script ya contiene la transacción; no combinarlo con `--single-transaction`.
`ON_ERROR_STOP` detiene el proceso y devuelve error si una sentencia falla.
Al cerrarse una conexión con transacción pendiente, PostgreSQL revierte sus cambios.

7. Inspeccionar con psql: `\dt tallerclaro.*`, `\d tallerclaro.pedido` y
   `\d tallerclaro.pago`. Deben existir exactamente seis tablas de negocio.
8. Crear una base separada `tallerclaro_test`, aplicar el mismo schema.sql allí y
   ejecutar `database/tests/schema_test.sql` con las mismas opciones de psql.

Antes de conectar FastAPI, crear un rol separado `tallerclaro_app` con LOGIN,
sin privilegios administrativos y con contraseña interactiva. Como propietario,
conceder USAGE del esquema, SELECT/INSERT/UPDATE sobre sus seis tablas y USAGE
en secuencias identity. No conceder CREATE, DELETE, TRUNCATE ni propiedad de tablas.
No conectar la aplicación como postgres ni como propietario. Este rol SQL no
sustituye la autorización de acceso por carpintero en FastAPI.

## 8. Datos de ejemplo y pruebas de aceptación

En `seeds/demo.sql`, usar INSERT con RETURNING y CTE o bloques PL/pgSQL para
obtener IDs. No asumir IDs consecutivos ni insertar valores identity explícitos.
Crear dos carpinteros, un cliente ficticio, una cotización y dos detalles:

- Material: cantidad 2.000 × 100.00 = 200.00.
- Mano de obra: cantidad 1.000 × 150.00 = 150.00.
- Total: 350.00 MXN; anticipo 175.00; saldo 175.00.

Crear un pedido pending y un intento de anticipo pending, con IDs PayPal NULL.
No insertar pagos completed con identificadores ficticios en los datos de demo:
las capturas simuladas pertenecen exclusivamente a la base de pruebas.

`schema_test.sql` tendrá BEGIN, bloques DO con aserciones y ROLLBACK final.
Cada fallo esperado se comprobará en un subbloque EXCEPTION que capture solo
el SQLSTATE esperado: 23502 NOT NULL, 23503 FK, 23505 UNIQUE, 23514 CHECK.
Si una operación inválida no falla, lanzar RAISE EXCEPTION para que falle la prueba.
No capturar WHEN OTHERS y continuar silenciosamente.

Casos obligatorios:

| Caso | Resultado esperado |
|---|---|
| Insertar flujo válido | PK generadas, relaciones correctas, total 350.00 |
| cantidad 0, negativa o NaN | Rechazo 23514 |
| precio negativo o NaN | Rechazo 23514 |
| cantidad 0.333 × precio 10.00 | importe 3.33 |
| Escribir importe generado | Rechazo de escritura de columna generada |
| Cotización con cliente inexistente | Rechazo 23503 |
| Pedido con otro carpintero | Rechazo 23503 por FK compuesta |
| Dos pedidos para la misma cotización | Rechazo 23505 |
| Código de pedido duplicado | Rechazo 23505 |
| Anticipo superior al total o negativo | Rechazo 23514 |
| Estado desconocido | Rechazo 23514 |
| Pago pending sin fecha ni IDs | Aceptado |
| Pago completed sin captura o fecha | Rechazo 23514 |
| Mismo paypal_order_id o capture_id en dos pagos | Rechazo 23505 |
| Varios intentos con IDs PayPal NULL | Aceptados |
| Reintento tras failed | Nueva fila permitida |
| Borrar cliente con cotizaciones o pedido con pagos | Rechazo 23503 |
| Actualizar cliente/cotización/pedido/pago | ultima_actualizacion se actualiza |
| Reaplicar schema.sql | Falla sin eliminar datos existentes |

La prueba de timestamps debe separar las dos sentencias y comprobar que el
valor previo se reemplazó; no esperar que now() cambie dentro de una transacción.
Tras ROLLBACK, no quedan fixtures; los contadores identity pueden avanzar.

Finalmente, revisar permisos con el rol de aplicación: lectura/escritura permitida,
CREATE TABLE y DELETE denegados. La consistencia de sumas, aprobación, bloqueo
de cotizaciones y concurrencia se probarán al implementar los casos de uso;
no son pruebas aprobadas por crear las seis tablas.

## 9. Cierre y documentación

- Ejecutar todas las pruebas en base nueva y guardar únicamente el resultado,
  nunca credenciales ni datos reales.
- Actualizar database/README.md con requisitos, comandos y diagrama ajustado.
- Actualizar el plan del backend: esquema implementado, conexión FastAPI pendiente.
- Documentar cambios al diagrama: email → correo, campos adicionales de moneda,
  captura y fechas, nullable de borradores y fecha_pago, FK compuesta.
- Revisar `git diff --check`, archivos staged y .gitignore antes del commit.
- El script termina esta entrega cuando crea las seis tablas y pasa las pruebas.
  No implica que los endpoints de negocio o los pagos estén implementados.

## Fuentes consultadas

Habilidad utilizada: supabase-postgres-best-practices (diseño, tipos, índices FK,
claves identity y mínimo privilegio). No requiere utilizar el servicio Supabase.

- https://www.postgresql.org/docs/current/ddl-constraints.html
- https://www.postgresql.org/docs/current/ddl-identity-columns.html
- https://www.postgresql.org/docs/current/ddl-generated-columns.html
- https://www.postgresql.org/docs/current/datatype-numeric.html
- https://www.postgresql.org/docs/current/datatype-datetime.html
- https://www.postgresql.org/docs/current/app-psql.html
- https://www.postgresql.org/docs/current/explicit-locking.html
