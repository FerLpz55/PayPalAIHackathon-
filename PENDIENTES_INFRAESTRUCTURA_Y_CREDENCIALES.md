# Pendientes de infraestructura y credenciales — TallerClaro

Actualizado: 9 de noviembre de 2026. No contiene valores de secretos ni datos `.env`. No se inspeccionaron archivos `.env`, vaults o credenciales de despliegue.

| Área | Estado comprobado | Requisito para la siguiente validación |
|---|---|---|
| PostgreSQL | Sin conexión realizada. `AGENTS.md` indica BD remota VPS/Coolify y prohíbe levantar PostgreSQL/Docker local. No se identificó una base descartable autorizada. | Proveer DSN/rol de una base de pruebas aislada, indicar si es descartable, versión/schema actual, owner y aprobación explícita de aplicar schema/migraciones. No usar production. |
| Backend API | Código local; no arrancado porque el lifespan espera DB y auth bcrypt. URL de staging no confirmada. | Host de staging, TLS, versión de API/OpenAPI y modo seguro de ejecutar pruebas. No usar endpoint/URL de producción. |
| Taller auth | Login Basic en memoria ya implementado en frontend y verificado solo con stub loopback; no hay credenciales reales ni validación con FastAPI. No existe login endpoint; se valida con GET protegido de órdenes. | Proveer backend de staging HTTPS y cuenta de taller de prueba autorizada; verificar CORS/auth/roles y acordar rotación/expiración. Basic permanece accesible al JavaScript del origen durante la pestaña; BFF/cookie HttpOnly sigue siendo una mejora de seguridad posible. |
| Customer token | Token permanece en sessionStorage; no hay email/link recovery verificado. | Política de emisión/entrega, scope, TTL, revocación, soporte cross-session y canal de notificación autorizado. |
| CORS | Default de fuente documentado anteriormente como comodín con credentials; configuración efectiva no inspeccionada. | Host exacto frontend/API staging y allowlist a configurar/verificar por infraestructura. |
| IA | No se contactó proveedor ni se leyeron secrets. | Cuenta/modelo/key de prueba y presupuesto/consentimiento; validar input/output, coste y errores solo en staging. |
| Channel3 | Lookup aparece asociado a catálogo/precios; proveedor no se verificó. | Confirmar si entra en alcance, proveedor/contrato/coste y credencial de prueba antes de validar “live”. |
| PayPal | Sandbox no conectado. No Live. | App/client/secret Sandbox, usuarios test, URLs de return/cancel HTTPS y API staging; aprobar casos de captura, duplicate/timeout y reconciliación. |
| Recibos/storage | No hay endpoint backend ni bytes; DEMO conserva nombres solamente. | Acordar modelo/permisos/MIME/tamaño/retención/storage antes de provisionar proveedor o DB. |
| GitHub/PR | La vista pública del repositorio abrió, pero las vistas de issues/PR no se recuperaron; `gh auth status` indicó token inválido y `git ls-remote` no conectó a GitHub. | Restablecer autenticación GitHub autorizada y acceso de red para consultar cuerpos/estado de issues #10–#28, comprobar PR relacionado y publicar la rama. No cerrar issues. |

## Límite local vigente

- Node 24.13.1, pnpm 12.16.1 y Python `Backend/.venv/Scripts/python.exe` 3.11.10 comprobados. El proyecto declara pnpm 12.14.0. Los comandos `pnpm run` no adquirieron el lock del store global; no se alteró configuración ni se instalaron deps.
- Vite 8.3.5 y ESLint disponibles. ESLint directo y build directo pasaron; Vitest no está en `frontend/node_modules`.
- Backend pytest: **314 passed** usando `--basetemp` dentro del workspace. Un primer intento sin esa opción falló por permiso denegado a Temp/cache del perfil; no es fallo de producto. La suite usa fakes y no prueba PostgreSQL real.
- Sin configuración segura local de PostgreSQL identificada. No se intentó conectar ni probar persistencia.

### Actualización Fase 8 — requisito pendiente

- No hay fallback Basic fijo en el cliente actual; las rutas de taller sin credenciales fallan con 401 local antes de enviar una solicitud. La ejecución con URL loopback ficticia confirmó el aviso y que REAL no cae a DEMO.
- El login Basic en memoria está implementado y probado con stub loopback (Fase 9). Falta validarlo con FastAPI staging HTTPS y cuenta temporal; no implica autenticación real verificada. La conclusión anterior de Fase 8 quedó superada.
- Evidencia: [Informe de autenticación Fase 8](INFORME_VERIFICACION_AUTH_FRONTEND_FASE_8.md).
