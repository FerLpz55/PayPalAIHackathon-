# Diagnóstico operativo de TallerClaro — Fase 0

**Fecha:** 9 de noviembre de 2026<br>
**Alcance:** comprobaciones locales y de solo lectura en `C:\Users\Usuario\Downloads\paypal\PayPalAIHackathon-`.<br>
**Referencia principal:** `C:\Users\Usuario\Downloads\paypal\AUDITORIA_TECNICA_PAYPAL_AI_HACKATHON.md`, informe completo del 9 de noviembre de 2026.<br>
**Documentación vigente:** `README.md`, `frontend/README.md`, `Backend/BACKENDREADME.md` y `database/README.md`.

## Alcance y método

Este diagnóstico complementa la auditoría técnica existente. No repite su revisión de arquitectura ni reescribe los hallazgos funcionales. Verifica el estado operativo observable en el entorno local y distingue entre configuración presente, acceso posible y funcionamiento probado.

No se instalaron dependencias, iniciaron servidores, ejecutaron pruebas, conectaron servicios, consultaron bases de datos, ejecutaron SQL ni inspeccionaron valores de secretos. Los archivos `.env` activos se buscaron por existencia y los nombres de variables se comprobaron sin mostrar valores. No se inspeccionaron los secretos de Vercel, Render ni proveedores.

Las etiquetas significan:

- **VERIFICADO:** comprobado directamente mediante inspección local no destructiva.
- **NO DISPONIBLE:** no está instalado/configurado en las ubicaciones locales inspeccionadas o no se encontró un listener local.
- **DESCONOCIDO:** no se puede concluir con la evidencia o acceso permitido.
- **REQUIERE AUTORIZACIÓN:** la comprobación siguiente necesitaría iniciar un proceso, instalar, hacer una conexión externa, ejecutar pruebas con posibles artefactos o alterar/consultar datos.

## Resumen operativo

| Área | Estado | Evidencia actual |
|---|---|---|
| Frontend: Node.js | **VERIFICADO** | `node --version` responde `v24.13.1`, dentro de la línea requerida `24.x`. |
| Frontend: pnpm | **DESCONOCIDO** | El comando `pnpm` existe como shim, pero `pnpm --version` falló al resolver el directorio bajo `C:\Users\Usuario` con acceso denegado. No se pudo verificar la versión activa ni ejecutar scripts. |
| Dependencias frontend | **VERIFICADO / PARCIAL** | Existe `frontend/node_modules` y metadatos instalados para React, React DOM, Vite, ESLint y el plugin de React. Vitest no está presente como paquete raíz, ejecutable ni carpeta del store `.pnpm`. La instalación no está completa para los scripts declarados. |
| Backend: Python y uv | **NO DISPONIBLE** | `python` no está en PATH, `py --list-paths` no encontró intérpretes y `uv` no está disponible como comando. No existe `Backend/.venv`. |
| Backend: dependencias | **NO DISPONIBLE** | Sin intérprete ni entorno virtual local no se pudo encontrar ni verificar una instalación de los requisitos Python del proyecto. |
| Configuración local | **NO DISPONIBLE** | No existen `frontend/.env`, sus variantes locales/de entorno, ni `Backend/.env`. Las variables listadas en las plantillas no aparecen configuradas en los ámbitos Process/User/Machine inspeccionados. |
| API local y PostgreSQL local | **NO DISPONIBLE** | `netstat` no mostró listeners en los puertos revisados: 8000, 5432, 5173 y 3000. No se iniciaron servicios. |
| PostgreSQL/Supabase remotos | **DESCONOCIDO** | No hay `DATABASE_URL` local. No se intentó conectividad ni inspección de esquema remoto. |
| IA, Channel3 y PayPal | **NO DISPONIBLE localmente / DESCONOCIDO en remoto** | No hay archivos de entorno activos ni variables locales de proveedor detectadas. La validez de credenciales y la configuración de entornos desplegados no se pueden verificar. |
| Git: estado, rama, commit y remoto | **DESCONOCIDO** | Git detuvo cada consulta por `dubious ownership`: el propietario del repositorio y el usuario actual tienen SID distintos. No se cambió la configuración de seguridad ni se intentó evitar el bloqueo. |
| Pruebas | **NO DISPONIBLE para ejecución en este entorno** | Hay suites frontend y backend en el árbol. Falta Vitest, y no hay Python/pytest. No se ejecutaron pruebas. |

**Conclusión operativa:** el frontend tiene partes de sus dependencias instaladas, pero no está listo para ejecutar toda su suite; el backend no puede arrancar en este entorno por falta de Python/uv, `.venv`, configuración local y disponibilidad demostrada de PostgreSQL. Ninguna integración real está verificada.

## Estado del frontend

### Versiones y dependencias

Requisitos declarados en `frontend/package.json` y `frontend/pnpm-lock.yaml`: Node `24.x`, pnpm `12.14.0`, React/React DOM `^19.3.1`, Vite `^8.3.5`, Vitest `^5.1.0`, ESLint `^10.13.0` y `@vitejs/plugin-react ^6.1.2`.

| Elemento | Estado | Evidencia |
|---|---|---|
| Node.js | **VERIFICADO** | Instalado: `v24.13.1`. |
| pnpm | **DESCONOCIDO** | El shim `pnpm.cmd` está instalado, pero la consulta de versión falla por acceso denegado durante la resolución de ruta. No afirmar que sea `12.14.0` en este equipo. |
| React | **VERIFICADO** | Instalado en `frontend/node_modules`: `19.3.1`. |
| React DOM | **VERIFICADO** | Instalado: `19.3.1`. |
| Vite | **VERIFICADO** | Instalado: `8.3.5`; existe `node_modules/.bin/vite`. |
| ESLint | **VERIFICADO** | Instalado: `10.14.0`, compatible con el rango declarado `^10.13.0`; existe su shim local. |
| Plugin React de Vite | **VERIFICADO** | El store local contiene `@vitejs/plugin-react 6.2.1`, que satisface el rango `^6.1.2`. |
| Vitest | **NO DISPONIBLE** | Está declarado, pero no existe `node_modules/vitest`, paquete `vitest` en el store local ni ejecutable `.bin/vitest`. La suite frontend no está lista para ejecutarse. |
| Carpeta `frontend/node_modules` | **VERIFICADO** | Presente. Su presencia no acredita instalación completa ni reproducible. |
| `frontend/dist` | **VERIFICADO, vigencia DESCONOCIDA** | Existe con fecha de modificación 3 de noviembre de 2026. Es un artefacto previo; no demuestra que corresponda al código actual ni que el build actual funcione. |
| Configuración frontend local | **NO DISPONIBLE** | No existe `frontend/.env` ni `.env.local`, `.env.development` o `.env.production`. `VITE_APP_MODE` y `VITE_API_BASE_URL` están ausentes en los ámbitos de entorno examinados. |

No se usó `pnpm install`, ni se ejecutó Vite, lint, build o Vitest. El bloqueo del shim debe resolverse antes de poder verificar el uso de las dependencias existentes. No se debe interpretar el contenido actual de `dist` como una aplicación conectada.

### Ejecución prevista (no ejecutada)

Desde `frontend/`, una vez que pnpm pueda ejecutarse y las dependencias estén completas:

```powershell
pnpm run dev
```

Para DEMO, configure `VITE_APP_MODE=demo` en el entorno de Vite. Para REAL se necesita `VITE_APP_MODE=real`, `VITE_API_BASE_URL` con el origen del backend, CORS compatible en backend y servicios backend operativos. No hay una URL de API local configurada ahora. El REAL mode y sus integraciones no se verificaron.

`pnpm run test` figura en `package.json`, pero no está disponible hasta resolver pnpm e instalar/restaurar Vitest. `pnpm run lint` y `pnpm run build` están declarados, pero no se ejecutaron; hacerlo requeriría autorización porque puede producir archivos/cache y el build actual escribe `frontend/dist`.

## Estado del backend

### Runtime y dependencias

`Backend/pyproject.toml` requiere Python `>=3.11`; el archivo `.python-version` y `render.yaml` fijan `3.11.10`. Las dependencias runtime declaradas son FastAPI, Pydantic Settings, Uvicorn, psycopg/pool, HTTPX, email-validator y bcrypt. El extra `dev` agrega pytest y pytest-asyncio; `requirements.txt` contiene una instalación editable del paquete.

| Elemento | Estado | Evidencia |
|---|---|---|
| Python de sistema | **NO DISPONIBLE** | `python --version` no se reconoce y `py --list-paths` responde que no hay Python instalado. |
| uv | **NO DISPONIBLE** | El comando no está en PATH. |
| `Backend/.venv` | **NO DISPONIBLE** | La ruta y el ejecutable Windows `Scripts/python.exe` no existen. Tampoco hay `Backend/venv`. |
| Dependencias backend | **NO DISPONIBLE** | No hay intérprete/entorno con que consultar paquetes; no se pueden considerar instaladas. |
| `Backend/.env` | **NO DISPONIBLE** | No existe. Solo está `Backend/.env.example`, que es plantilla, no configuración activa. |
| Arranque FastAPI | **NO DISPONIBLE actualmente** | Faltan Python/uv, entorno, variables requeridas y una base accesible confirmada. No se inició el servidor. |

La inspección confirma una contradicción documental: `AGENTS.md` dice que existe `Backend/.venv` con Python 3.14. En este checkout el directorio no existe y no hay intérprete Python detectable. Por tanto, aquella instrucción no describe el entorno operativo observado y no se usó como evidencia de instalación.

### Ejecución prevista (no ejecutada)

Una vez instalado Python 3.11.10 o compatible y `uv`, creadas las variables necesarias y disponible una base compatible, la documentación vigente indica ejecutar desde `Backend/`:

```powershell
uv venv .venv
.venv\Scripts\Activate.ps1
uv pip install -e '.[dev]'
Copy-Item .env.example .env
fastapi dev src/tallerclaro/main.py
```

Estos comandos no se ejecutaron. La copia de `.env.example` no basta para arrancar: se requieren una configuración de PostgreSQL accesible y un hash bcrypt de taller válido. No se creó ni sobrescribió `.env`.

## PostgreSQL y persistencia

| Elemento | Estado | Evidencia |
|---|---|---|
| Configuración local de conexión | **NO DISPONIBLE** | No hay `Backend/.env`, `DATABASE_URL`, alias de conexión ni variables individuales de DB en los entornos locales examinados. |
| PostgreSQL en loopback | **NO DISPONIBLE** | `netstat` no mostró listeners locales en `5432` en el instante de la consulta. |
| PostgreSQL remoto / Supabase | **DESCONOCIDO** | No se hizo conexión ni consulta de red. No se puede afirmar existencia, accesibilidad, versión, disponibilidad ni permisos. |
| Esquema en instancia real | **DESCONOCIDO** | No se consultó una base. El contenido de `database/schema.sql` y migraciones solo documenta el estado esperado del código, no el estado de una instancia desplegada. |
| Prueba SQL | **REQUIERE AUTORIZACIÓN** | `database/tests/schema_test.sql` ejecuta SQL y requiere una base objetivo. No se ejecutó. Las migraciones tampoco se ejecutaron. |

La auditoría técnica y el README de base de datos indican que el backend falla al iniciar si no puede establecer su conexión inicial y que no hay runner de migraciones. No se puede validar el esquema desplegado ni su compatibilidad con la migración `003` sin acceso aprobado a la instancia y consultas de solo lectura dirigidas a un host confirmado.

## Entornos, configuración y credenciales

### Archivos y variables locales

Están presentes `frontend/.env.example` y `Backend/.env.example`. No se encontraron los archivos locales activos `frontend/.env`, variantes locales/de desarrollo/producción, ni `Backend/.env`. En las variables de entorno Process/User/Machine inspeccionadas no aparecen configuradas las variables frontend/backend documentadas. No se mostró ningún valor.

| Grupo | Estado local | Validez / entorno remoto |
|---|---|---|
| `VITE_APP_MODE`, `VITE_API_BASE_URL` | **NO DISPONIBLE** | URL desplegada y configuración Vercel: **DESCONOCIDO**. |
| PostgreSQL (`DATABASE_URL` o `TALLERCLARO_DATABASE_*`) | **NO DISPONIBLE** | Credencial/host y esquema remoto: **DESCONOCIDO**. |
| Auth de taller y tokens (`TALLERCLARO_WORKSHOP_*`, `TALLERCLARO_CUSTOMER_TOKEN_SECRET`) | **NO DISPONIBLE** | Validez de hashes/secretos remotos: **DESCONOCIDO**. |
| CORS (`TALLERCLARO_CORS_ORIGINS`) | **NO DISPONIBLE** en entorno local | Allowlist de despliegues: **DESCONOCIDO**. |
| IA (`TALLERCLARO_AI_*`) | **NO DISPONIBLE** localmente | Cuenta, llave, cuotas y respuesta del proveedor: **DESCONOCIDO**. |
| Channel3 (`TALLERCLARO_PRICE_LOOKUP_*`) | **NO DISPONIBLE** localmente | Cuenta, llave, cuotas y accesibilidad de API: **DESCONOCIDO**. |
| PayPal (`TALLERCLARO_PAYPAL_*`) | **NO DISPONIBLE** localmente | Credenciales Sandbox, URLs y cuenta de despliegue: **DESCONOCIDO**. No hubo operaciones de pago. |

La ausencia local no demuestra que falten secretos en los paneles de Render/Vercel o en otro gestor; no se accedió a esas cuentas. Una variable no vacía, si apareciera en otro entorno, tampoco acreditaría que el secreto sea válido o tenga permisos.

### Desarrollo, staging y producción

- **Local:** los archivos de configuración del frontend y backend existen, pero sus variables locales no; no se halló listener API o PostgreSQL. El modo DEMO está implementado en el código, pero su ejecución depende de resolver el problema de pnpm. Backend REAL no está listo para arrancar.
- **Staging:** **DESCONOCIDO**. No se encontraron URL/credenciales accesibles ni se hicieron consultas externas.
- **Producción:** **DESCONOCIDO**. `frontend/vercel.json` y `render.yaml` definen configuraciones de despliegue, pero no demuestran que existan deployments activos, variables configuradas o URLs accesibles. No se encontraron comandos `vercel` ni `render` en PATH.

## Servicios externos

| Servicio | Declarado/implementado en código | Configurado localmente | Accesible/funcional |
|---|---|---|---|
| PostgreSQL/Supabase | Cliente psycopg, configuración y SQL presentes (**VERIFICADO en fuente**) | **NO DISPONIBLE** | **DESCONOCIDO**; no hubo conexión ni lectura de esquema. |
| Proveedor IA | Adaptadores HTTPX y nombres de proveedor/modelo documentados (**VERIFICADO en fuente**) | **NO DISPONIBLE**; proveedor predeterminado `none` según README/código auditado | **DESCONOCIDO**; no se consultó proveedor. |
| Channel3 | Adaptador de búsqueda y variables documentados (**VERIFICADO en fuente**) | **NO DISPONIBLE**; proveedor predeterminado `none` | **DESCONOCIDO**; no se hizo búsqueda. |
| PayPal Sandbox | OAuth/Orders v2 del lado servidor presente (**VERIFICADO en fuente**) | **NO DISPONIBLE**; modo predeterminado `none`, sin variables locales activas | **DESCONOCIDO**; no se solicitaron tokens ni se efectuaron operaciones. |
| Vercel | `frontend/vercel.json` presente (**VERIFICADO**) | **DESCONOCIDO** | Deployment/acceso/funcionalidad: **DESCONOCIDO**. |
| Render | `render.yaml` presente (**VERIFICADO**) | **DESCONOCIDO** | Deployment/acceso/funcionalidad: **DESCONOCIDO**. |

## Git y archivos

El comando `git status --short --branch` y las consultas de rama/commit/upstream fueron rechazados por la protección `safe.directory`: Git detectó que el repositorio pertenece al SID `...-1001` y el usuario actual es `...-1004`. No se añadió una excepción, no se modificó configuración Git y no se intentó consultar Git con un bypass.

Por lo tanto, son **DESCONOCIDOS** el estado exacto del árbol, la rama, el commit local y la diferencia con el upstream remoto. No se ejecutó `fetch` ni se contactó al remoto. La lista al final indica el archivo creado en esta fase; no sustituye un `git status` completo. Los README vigentes se leyeron sin modificarlos durante esta fase.

## Pruebas y capacidad de verificación

| Suite / verificación | Disponible en el código | Se puede ejecutar ahora | Decisión |
|---|---|---|---|
| Frontend Vitest | Sí: scripts en `frontend/package.json` y pruebas en `frontend/src/**/__tests__` | **NO DISPONIBLE**: falta Vitest instalado y pnpm no puede ejecutar su consulta de versión | No ejecutar; requiere resolver pnpm y restaurar dependencias. |
| Frontend lint/build | Scripts `pnpm run lint` y `pnpm run build` declarados; ESLint/Vite presentes en el árbol | **DESCONOCIDO** hasta que pnpm funcione | No ejecutar: lint/build pueden escribir cachés/artefactos y el build escribe `frontend/dist`. |
| Backend pytest | Suite en `Backend/tests`, comandos descritos en `Backend/pyproject.toml` y README | **NO DISPONIBLE**: no hay intérprete Python, uv, `.venv` ni pytest verificable | No ejecutar. Los tests usan fakes según README, pero eso no acredita servicios reales. |
| SQL acceptance | `database/tests/schema_test.sql` presente | Requiere una base objetivo y ejecuta SQL aunque el script use rollback | **REQUIERE AUTORIZACIÓN**; no ejecutar en esta fase. |
| E2E / servicios externos | No hay script E2E frontend descrito en los README vigentes | **DESCONOCIDO / no configurado** | Requeriría autorización, entorno de staging y credenciales. No se intentó. |

No se ejecutó ninguna prueba, lint, build, migración, petición HTTP ni operación contra un servicio. No se afirma ningún resultado de aprobación.

## Bloqueos concretos y riesgos operativos

1. Git impide inspeccionar estado, rama y commit debido a la protección de propiedad; no se cambió esa protección.
2. El comando pnpm no puede resolver su ruta por acceso denegado; además, Vitest está ausente del árbol instalado.
3. No hay Python/uv ni entorno virtual de backend; por tanto, backend y pytest no pueden arrancar aquí.
4. No hay configuración `.env` activa ni URL local de API o base de datos; la aplicación REAL carece de datos de conexión locales.
5. No hay listener local en los puertos revisados; no se inició ningún proceso.
6. No se dispone de evidencia sobre staging/producción o valores configurados en Vercel/Render. Las plantillas y manifests no prueban despliegues.
7. No se validaron esquema, migraciones ni credenciales externas; el backend puede seguir fallando durante startup aunque el código compile.
8. `frontend/dist` es anterior a esta inspección; no debe usarse como evidencia del estado actual ni desplegarse como build verificado.
9. La guía `AGENTS.md` afirma que existe un entorno `.venv` con Python 3.14, contradicho por el estado local observado y por el requisito `>=3.11` del backend. Se debe actualizar esa referencia fuera de esta fase documental solo cuando se autorice.

## Comandos de arranque documentados

Los siguientes son los comandos del proyecto, no se ejecutaron y no bastan por sí solos hasta satisfacer los prerequisitos indicados.

**Frontend DEMO**, desde `frontend/` (requiere pnpm ejecutable y dependencias completas):

```powershell
$env:VITE_APP_MODE = 'demo'
pnpm run dev
```

**Frontend REAL**, desde `frontend/` (requiere backend accesible y CORS configurado):

```powershell
$env:VITE_APP_MODE = 'real'
$env:VITE_API_BASE_URL = '<backend-origin-configurado>'
pnpm run dev
```

No guardar secretos en variables `VITE_*`; se compilan en assets públicos.

**Backend**, desde `Backend/` (requiere Python, uv, entorno, configuración, hash bcrypt válido y PostgreSQL/schema compatibles):

```powershell
uv venv .venv
.venv\Scripts\Activate.ps1
uv pip install -e '.[dev]'
# Preparar .env con valores obtenidos/aprobados por el equipo, sin publicar secretos.
fastapi dev src/tallerclaro/main.py
```

La creación/configuración de `.env`, instalación, arranque y comprobaciones de conectividad quedaron fuera de esta autorización y requieren aprobación posterior.

## Plan recomendado para la Fase 1

1. **Restablecer visibilidad Git:** pedir al propietario del entorno que resuelva el acceso de forma aprobada; no cambiar `safe.directory` desde este diagnóstico. Entonces registrar estado, rama, SHA y upstream sin `fetch` inicialmente.
2. **Resolver toolchain local:** habilitar el acceso de pnpm y comprobar `12.14.0`; instalar/seleccionar Python `3.11.10` y uv. Requiere autorización explícita para instalar o cambiar PATH/runtime.
3. **Reproducir frontend:** con aprobación, instalar desde `pnpm-lock.yaml` en modo frozen, verificar Vitest, después lint y build y registrar si `dist` se regeneró.
4. **Preparar backend sin tocar servicios compartidos:** crear entorno aislado e instalar desde `pyproject.toml`/`uv.lock`; configurar secretos fuera del repositorio. No copiar valores reales al informe.
5. **Acordar entorno DB objetivo:** solicitar al responsable la URL de staging por un canal seguro, versión, usuario/rol, esquema y ventana aprobada. Primero comprobar conectividad y esquema con consultas de solo lectura; no migrar.
6. **Verificar API local/staging:** iniciar solo después de aprobarlo; comprobar health, disponibilidad DB, CORS y autenticación por separado. Health no equivale a readiness de DB.
7. **Validar proveedores en sandbox:** confirmar proveedor/modelo de IA y Channel3; probarlos solo con autorización y límites definidos. Validar PayPal Sandbox con credenciales sandbox, nunca live ni pagos reales.
8. **Ejecutar suites por etapas:** comenzar con unitarias/fakes tras aprobación para artefactos locales; después integración en DB descartable, y finalmente E2E en staging. No usar SQL acceptance ni pruebas que escriban contra producción.
9. **Cerrar con matriz evidencia:** registrar para cada dependencia si está declarada, instalada, configurada, accesible y funcional; adjuntar salidas saneadas sin tokens ni URLs sensibles.

## Archivos modificados

Archivo nuevo creado durante esta fase:

- `DIAGNOSTICO_OPERATIVO_FASE_0.md` — este informe.

No se modificaron los cuatro README, el informe de auditoría previo, código, dependencias, configuraciones ni SQL. Git no permitió verificar el listado completo del árbol por el bloqueo de propiedad descrito arriba; por eso la lista del estado total del repositorio queda **DESCONOCIDA** hasta que Git pueda consultarse de forma aprobada.

## Recomendación y cierre

El siguiente paso recomendado es resolver primero el bloqueo local de Git y pnpm, y habilitar Python/uv. Después, solicitar al responsable de infraestructura los datos de staging por un canal seguro para comprobar PostgreSQL/API en modo de solo lectura antes de cualquier migración o prueba de escritura.

Este diagnóstico termina aquí. No se corrigieron errores ni se inició la Fase 1.
