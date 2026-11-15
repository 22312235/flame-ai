-- ============================================================
-- Migration: 002_document_schema
-- Description: Document extraction and structured content tables
-- ============================================================


-- ------------------------------------------------------------
-- 1. Documents
-- ------------------------------------------------------------

CREATE TABLE documents (
    document_id UUID PRIMARY KEY,
    file_id UUID NOT NULL UNIQUE,

    title VARCHAR(1000),
    author VARCHAR(500),
    principal_investigator VARCHAR(500),

    extracted_text TEXT,
    extraction_method VARCHAR(50),

    metadata JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_documents_file
        FOREIGN KEY (file_id)
        REFERENCES files(file_id)
        ON DELETE CASCADE
);

CREATE INDEX ix_documents_file_id
    ON documents(file_id);


-- ------------------------------------------------------------
-- 2. Document units: pages, slides, and sections
-- ------------------------------------------------------------

CREATE TABLE document_units (
    unit_id UUID PRIMARY KEY,
    document_id UUID NOT NULL,

    unit_type VARCHAR(30) NOT NULL,
    unit_number INTEGER NOT NULL,

    title VARCHAR(1000),
    extracted_text TEXT,

    metadata JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_document_units_document
        FOREIGN KEY (document_id)
        REFERENCES documents(document_id)
        ON DELETE CASCADE,

    CONSTRAINT uq_document_unit_number
        UNIQUE (document_id, unit_type, unit_number)
);

CREATE INDEX ix_document_units_document_id
    ON document_units(document_id);


-- ------------------------------------------------------------
-- 3. PSI fields
-- ------------------------------------------------------------

CREATE TABLE psi_fields (
    psi_field_id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    unit_id UUID,

    name VARCHAR(300) NOT NULL,
    value JSONB NOT NULL,
    field_type VARCHAR(50),

    source_text TEXT,
    metadata JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_psi_fields_document
        FOREIGN KEY (document_id)
        REFERENCES documents(document_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_psi_fields_unit
        FOREIGN KEY (unit_id)
        REFERENCES document_units(unit_id)
        ON DELETE SET NULL
);

CREATE INDEX ix_psi_fields_document_id
    ON psi_fields(document_id);

CREATE INDEX ix_psi_fields_unit_id
    ON psi_fields(unit_id);

CREATE INDEX ix_psi_fields_name
    ON psi_fields(name);


-- ------------------------------------------------------------
-- 4. Document references
-- ------------------------------------------------------------

CREATE TABLE document_references (
    reference_id UUID PRIMARY KEY,
    document_id UUID NOT NULL,

    doi VARCHAR(500),
    title VARCHAR(1000),

    authors JSONB NOT NULL,

    publication_year INTEGER,
    url TEXT,
    citation_text TEXT,

    metadata JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_document_references_document
        FOREIGN KEY (document_id)
        REFERENCES documents(document_id)
        ON DELETE CASCADE
);

CREATE INDEX ix_document_references_document_id
    ON document_references(document_id);

CREATE INDEX ix_document_references_doi
    ON document_references(doi);


-- ------------------------------------------------------------
-- 5. Extracted tables
-- ------------------------------------------------------------

CREATE TABLE extracted_tables (
    table_id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    unit_id UUID,

    table_number INTEGER NOT NULL,
    title VARCHAR(1000),

    headers JSONB NOT NULL,
    rows JSONB NOT NULL,
    metadata JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_extracted_tables_document
        FOREIGN KEY (document_id)
        REFERENCES documents(document_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_extracted_tables_unit
        FOREIGN KEY (unit_id)
        REFERENCES document_units(unit_id)
        ON DELETE SET NULL
);

CREATE INDEX ix_extracted_tables_document_id
    ON extracted_tables(document_id);

CREATE INDEX ix_extracted_tables_unit_id
    ON extracted_tables(unit_id);


-- ------------------------------------------------------------
-- 6. Extracted charts
-- ------------------------------------------------------------

CREATE TABLE extracted_charts (
    chart_id UUID PRIMARY KEY,
    document_id UUID NOT NULL,
    unit_id UUID,

    title VARCHAR(1000),
    chart_type VARCHAR(100),

    metadata JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_extracted_charts_document
        FOREIGN KEY (document_id)
        REFERENCES documents(document_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_extracted_charts_unit
        FOREIGN KEY (unit_id)
        REFERENCES document_units(unit_id)
        ON DELETE SET NULL
);

CREATE INDEX ix_extracted_charts_document_id
    ON extracted_charts(document_id);

CREATE INDEX ix_extracted_charts_unit_id
    ON extracted_charts(unit_id);


-- ------------------------------------------------------------
-- 7. Chart series
-- ------------------------------------------------------------

CREATE TABLE chart_series (
    series_id UUID PRIMARY KEY,
    chart_id UUID NOT NULL,

    name VARCHAR(500),

    x_values JSONB NOT NULL,
    y_values JSONB NOT NULL,

    x_unit VARCHAR(100),
    y_unit VARCHAR(100),

    metadata JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_chart_series_chart
        FOREIGN KEY (chart_id)
        REFERENCES extracted_charts(chart_id)
        ON DELETE CASCADE
);

CREATE INDEX ix_chart_series_chart_id
    ON chart_series(chart_id);