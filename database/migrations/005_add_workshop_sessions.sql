-- Migracion 005: sesiones revocables del taller.
-- Ejecutar en Supabase SQL Editor con autorizacion explicita.
--
-- Solo se guarda el hash SHA-256 del token opaco. La huella de credenciales
-- invalida automaticamente las sesiones cuando cambia el hash bcrypt del taller.
-- No se guarda el token en claro ni se crea un token de sesion por peticion.

BEGIN;

CREATE TABLE IF NOT EXISTS tallerclaro.sesion_taller (
    id_sesion             bigint GENERATED ALWAYS AS IDENTITY,
    id_carpintero         bigint NOT NULL,
    token_hash            text NOT NULL,
    credencial_huella     text NOT NULL,
    fecha_creacion        timestamptz NOT NULL DEFAULT now(),
    ultimo_uso            timestamptz NOT NULL DEFAULT now(),
    fecha_expiracion      timestamptz NOT NULL,
    revocada_en           timestamptz,

    CONSTRAINT pk_sesion_taller PRIMARY KEY (id_sesion),
    CONSTRAINT fk_sesion_taller_carpintero FOREIGN KEY (id_carpintero)
        REFERENCES tallerclaro.carpintero (id_carpintero)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT uq_sesion_taller_token_hash UNIQUE (token_hash),
    CONSTRAINT ck_sesion_taller_token_hash_no_vacio CHECK (btrim(token_hash) <> ''),
    CONSTRAINT ck_sesion_taller_huella_no_vacia CHECK (btrim(credencial_huella) <> ''),
    CONSTRAINT ck_sesion_taller_fechas CHECK (fecha_expiracion > fecha_creacion)
);

COMMENT ON TABLE tallerclaro.sesion_taller IS
    'Sesiones opacas del taller; se almacena solo el hash del token.';
COMMENT ON COLUMN tallerclaro.sesion_taller.credencial_huella IS
    'SHA-256 del hash bcrypt vigente; cambiar la contrasena revoca las sesiones.';

CREATE INDEX IF NOT EXISTS ix_sesion_taller_vigente
    ON tallerclaro.sesion_taller (token_hash)
    WHERE revocada_en IS NULL;

-- Paridad con schema.sql y el rol de aplicacion (sin DELETE).
DO $permisos$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tallerclaro_app') THEN
        GRANT SELECT, INSERT, UPDATE ON TABLE tallerclaro.sesion_taller TO tallerclaro_app;
        EXECUTE format(
            'GRANT USAGE ON SEQUENCE %s TO tallerclaro_app',
            pg_get_serial_sequence('tallerclaro.sesion_taller', 'id_sesion')
        );
    END IF;
END;
$permisos$;

COMMIT;
