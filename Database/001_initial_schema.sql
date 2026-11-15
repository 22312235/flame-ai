-- =========================================================
-- 001_initial_schema.sql
-- Flame project: Initial database schema
-- =========================================================


-- =========================================================
-- 1. INVESTIGATIONS
-- =========================================================

CREATE TABLE investigations (
    investigation_id UUID PRIMARY KEY,

    external_id VARCHAR(150) UNIQUE,

    title VARCHAR(500) NOT NULL,

    description TEXT,

    principal_investigator VARCHAR(300),

    start_date DATE,

    end_date DATE,

    metadata JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,

    updated_at TIMESTAMPTZ NOT NULL
);


-- =========================================================
-- 2. FILES
-- =========================================================

CREATE TABLE files (
    file_id UUID PRIMARY KEY,

    investigation_id UUID NOT NULL,

    parent_file_id UUID,

    filename VARCHAR(500) NOT NULL,

    extension VARCHAR(30),

    detected_format VARCHAR(100),

    file_category VARCHAR(50) NOT NULL,

    file_role VARCHAR(50) NOT NULL,

    storage_path TEXT NOT NULL,

    file_size_bytes BIGINT NOT NULL,

    sha256 VARCHAR(64),

    processing_status VARCHAR(30) NOT NULL,

    registered_at TIMESTAMPTZ NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,

    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_files_investigation
        FOREIGN KEY (investigation_id)
        REFERENCES investigations(investigation_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_files_parent
        FOREIGN KEY (parent_file_id)
        REFERENCES files(file_id)
        ON DELETE SET NULL
);


-- =========================================================
-- 3. PROCESSING JOBS
-- =========================================================

CREATE TABLE processing_jobs (
    job_id UUID PRIMARY KEY,

    file_id UUID NOT NULL,

    processor_type VARCHAR(100) NOT NULL,

    processor_version VARCHAR(50),

    status VARCHAR(30) NOT NULL,

    started_at TIMESTAMPTZ,

    completed_at TIMESTAMPTZ,

    error_message TEXT,

    warnings JSONB NOT NULL,

    processing_parameters JSONB NOT NULL,

    created_at TIMESTAMPTZ NOT NULL,

    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_processing_jobs_file
        FOREIGN KEY (file_id)
        REFERENCES files(file_id)
        ON DELETE CASCADE
);


-- =========================================================
-- 4. INDEXES
-- =========================================================

-- Investigations

CREATE INDEX ix_investigations_external_id
    ON investigations(external_id);


-- Files

CREATE INDEX ix_files_investigation_id
    ON files(investigation_id);

CREATE INDEX ix_files_parent_file_id
    ON files(parent_file_id);

CREATE INDEX ix_files_sha256
    ON files(sha256);

CREATE INDEX ix_files_investigation_category
    ON files(investigation_id, file_category);

CREATE INDEX ix_files_investigation_role
    ON files(investigation_id, file_role);


-- Processing jobs

CREATE INDEX ix_processing_jobs_file_id
    ON processing_jobs(file_id);

CREATE INDEX ix_processing_jobs_status
    ON processing_jobs(status);

CREATE INDEX ix_processing_jobs_file_status
    ON processing_jobs(file_id, status);