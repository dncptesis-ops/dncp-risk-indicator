
-- =========================================================================================
-- SCHEMA OCDS - DNCP PORTAL DATOS ABIERTOS (NORMALIZADO)
-- Generado: 2026-09-28
-- =========================================================================================

-- ============================================================
-- 1. MÓDULO DE CONTROL Y AUDITORÍA
-- ============================================================
CREATE TABLE IF NOT EXISTS etl_runs (
    table_name      TEXT,
    file_name       TEXT,       -- carpeta del año y archivo, ej. 2024/records.csv
    file_hash       TEXT NOT NULL,          -- MD5 para detectar cambios en el archivo
    processed_at    TIMESTAMPTZ DEFAULT NOW(),
    status          TEXT DEFAULT 'SUCCESS',
    PRIMARY KEY (file_name, table_name) -- Clave compuesta
);

CREATE TABLE IF NOT EXISTS sync_log (
    id              BIGSERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'running',   -- 'running','success','failed'
    records_processed INT DEFAULT 0,
    last_release_date TIMESTAMPTZ,                     -- fecha máxima procesada en esta ejecución
    error_message   TEXT,
    CHECK (status IN ('running','success','failed'))
);

-- ============================================================
-- 2. TABLA RAÍZ (CORE)
-- ============================================================
CREATE TABLE IF NOT EXISTS releases (
    release_id      TEXT PRIMARY KEY,       -- compiledRelease/id, id de la version (un ocid puede tener varias)
    ocid            TEXT NOT NULL,
    date            TIMESTAMPTZ,
    language        TEXT,
    source_file     TEXT -- de donde vino: 2024/records.csv o api_sync
);
-- Mismo orden que la retención y que latest_releases: version mas nueva primero
CREATE INDEX IF NOT EXISTS idx_releases_ocid_date
    ON releases (ocid, date DESC NULLS LAST, (COALESCE(source_file = 'api_sync', false)) DESC, release_id DESC);

-- ============================================================
-- 3. MÓDULO PARTIES (Entidades, Proveedores, Compradores)
-- ============================================================
-- Viene de parties.csv
CREATE TABLE IF NOT EXISTS parties (
    release_id      TEXT REFERENCES releases(release_id) ON DELETE CASCADE,
    party_id        TEXT,                   -- id original (ej. PY-RUC-...)
    name            TEXT,
    identifier_id   TEXT,                   -- RUC o Documento
    identifier_scheme TEXT,                 -- PY-RUC, DNCP-SICP-CODE, PY-CI
    identifier_legal_name TEXT,             -- Razon social declarada por el proveedor
    address_country TEXT,
    address_locality TEXT,                  -- Distrito / localidad
    address_region  TEXT,                   -- Departamento
    address_street_address TEXT,
    contact_name    TEXT,
    contact_email   TEXT,
    contact_phone   TEXT,
    contact_url     TEXT,
    contact_fax     TEXT,
    details_level   TEXT,                   -- Poder Ejecutivo, Municipalidades, ...
    details_entity_type TEXT,               -- Organismos de la Administracion Central, Entidades Descentralizadas, ...
    details_type    TEXT,                   -- Entidad o Unidad Contratación
    details_scale   TEXT,                   -- tamaño de la empresa: micro, sme, large
    details_legal_entity_type_detail TEXT,  -- Persona Física, S.A., S.R.L., ...
    details_activity_types TEXT,            -- goods, services o goods;services
    PRIMARY KEY (release_id, party_id)
);
CREATE INDEX IF NOT EXISTS idx_parties_identifier ON parties(identifier_id);
CREATE INDEX IF NOT EXISTS idx_party_id ON parties (party_id);
CREATE INDEX IF NOT EXISTS idx_parties_email ON parties(contact_email);

-- Roles de cada party (columna roles de parties.csv, separada por ;)
CREATE TABLE IF NOT EXISTS party_roles (
    release_id      TEXT,
    party_id        TEXT,
    role            TEXT,                   -- buyer, procuringEntity, tenderer, supplier, payer, ...
    PRIMARY KEY (release_id, party_id, role),
    FOREIGN KEY (release_id, party_id) REFERENCES parties(release_id, party_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_party_roles_role ON party_roles (role, release_id, party_id);

-- ============================================================
-- 4. MÓDULO TENDER (Licitación)
-- ============================================================
-- Viene de records.csv
CREATE TABLE IF NOT EXISTS tender (
    release_id                  TEXT PRIMARY KEY REFERENCES releases(release_id) ON DELETE CASCADE,
    tender_id                   TEXT,
    title                       TEXT,
    status                      TEXT,
    value_amount                NUMERIC(24,2),
    value_currency              TEXT,
    procurement_method          TEXT,
    procurement_method_details  TEXT,
    main_procurement_category   TEXT,       -- goods, works, services
    submission_method           TEXT,       -- inPerson, electronicAuction
    has_electronic_auction      BOOLEAN,    -- Convertido desde texto en ETL
    tender_period_start_date    TIMESTAMPTZ,
    tender_period_end_date      TIMESTAMPTZ,
    duration_in_days            INTEGER,
    number_of_tenderers         INTEGER,
    eligibility_criteria        TEXT
);
CREATE INDEX IF NOT EXISTS idx_tender_dates ON tender(tender_period_start_date, tender_period_end_date);
CREATE INDEX IF NOT EXISTS idx_tender_status ON tender(status);
CREATE INDEX IF NOT EXISTS idx_tender_filter ON tender (procurement_method, COALESCE(tender_period_end_date, tender_period_start_date));

-- ============================================================
-- 5. MÓDULO OFERENTES (Tenderers)
-- ============================================================
CREATE TABLE IF NOT EXISTS tenderers (
    release_id      TEXT,
    tenderer_id     TEXT,                   -- Se une con parties.party_id
    name            TEXT,
    PRIMARY KEY (release_id, tenderer_id),
    FOREIGN KEY (release_id) REFERENCES releases(release_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_tenderers_id ON tenderers(tenderer_id);

-- ============================================================
-- 6. MÓDULO CONTRACTS (Contratos y Modificaciones)
-- ============================================================
CREATE TABLE IF NOT EXISTS contracts (
    release_id      TEXT,
    contract_id     TEXT,
    award_id        TEXT,
    status          TEXT,
    value_amount    NUMERIC(24,2),
    value_currency  TEXT,
    date_signed     TIMESTAMPTZ,
    period_start_date TIMESTAMPTZ,
    period_end_date TIMESTAMPTZ,
    duration_in_days INTEGER,
    PRIMARY KEY (release_id, contract_id),
    FOREIGN KEY (release_id) REFERENCES releases(release_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_contracts_date_only ON contracts ( (COALESCE(date_signed, period_start_date)) );

-- Viene de con_amendments.csv
CREATE TABLE IF NOT EXISTS contract_amendments (
    release_id      TEXT,
    contract_id     TEXT,
    amendment_id    TEXT,
    date            TIMESTAMPTZ,
    description     TEXT,
    amends_amount   NUMERIC(24,2),
    amends_currency TEXT,
    rationale       TEXT,
    guarantee_type  TEXT,
    PRIMARY KEY (release_id, contract_id, amendment_id),
    FOREIGN KEY (release_id, contract_id) REFERENCES contracts(release_id, contract_id) ON DELETE CASCADE
);

-- Viene de con_documents.csv
CREATE TABLE IF NOT EXISTS contract_documents (
    release_id              TEXT,
    contract_id             TEXT,
    document_id             TEXT,
    document_type           TEXT,
    document_type_details   TEXT,
    title                   TEXT,
    url                     TEXT,
    language                TEXT,
    date_published          TIMESTAMPTZ,
    PRIMARY KEY (release_id, contract_id, document_id),
    FOREIGN KEY (release_id, contract_id) REFERENCES contracts(release_id, contract_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_contract_docs_type ON contract_documents(document_type);

-- ============================================================
-- 7. Vistas
-- ============================================================
-- Versión vigente de cada proceso (una fila por ocid). Mismo orden que la
-- retención: fecha, después la versión de la API, después release_id.
CREATE OR REPLACE VIEW latest_releases AS
SELECT DISTINCT ON (ocid) *
FROM releases
ORDER BY ocid, date DESC NULLS LAST, COALESCE(source_file = 'api_sync', false) DESC, release_id DESC;

-- Nombre más reciente de cada entidad (party_id) en todo el corpus.
CREATE MATERIALIZED VIEW IF NOT EXISTS party_master AS
SELECT party_id, name, identifier_id, identifier_legal_name, address_country, contact_email
FROM (
    SELECT p.*, r.date,
           ROW_NUMBER() OVER (
               PARTITION BY p.party_id
               ORDER BY r.date DESC NULLS LAST, COALESCE(r.source_file = 'api_sync', false) DESC, r.release_id DESC
           ) AS rn
    FROM parties p
    JOIN releases r ON p.release_id = r.release_id
    WHERE p.name IS NOT NULL
) sub
WHERE rn = 1;
CREATE UNIQUE INDEX IF NOT EXISTS party_master_party_id_idx ON party_master (party_id);

-- ============================================================
-- 8. configuracion de timezone
-- ============================================================

DO $$
BEGIN
    EXECUTE 'ALTER DATABASE ' || current_database() || ' SET timezone TO ''UTC''';
END;
$$;
