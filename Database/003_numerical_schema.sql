CREATE TABLE datasets (
    dataset_id UUID PRIMARY KEY,
    file_id UUID NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,
    processor_dataset_id VARCHAR(300) NOT NULL,
    source_file VARCHAR(500) NOT NULL,
    source_format VARCHAR(30) NOT NULL,
    sheet_name VARCHAR(300),
    row_count INTEGER NOT NULL,
    column_count INTEGER NOT NULL,
    duplicate_rows INTEGER NOT NULL DEFAULT 0,
    duplicate_rows_removed INTEGER NOT NULL DEFAULT 0,
    empty_rows_removed INTEGER NOT NULL DEFAULT 0,
    empty_columns_removed INTEGER NOT NULL DEFAULT 0,
    parquet_path TEXT,
    profile_path TEXT,
    status VARCHAR(30) NOT NULL,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    processed_at TIMESTAMPTZ,
    profile_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_dataset_file_processor_id
        UNIQUE (file_id, processor_dataset_id)
);

CREATE INDEX ix_datasets_file_id
    ON datasets(file_id);

CREATE INDEX ix_datasets_source_format
    ON datasets(source_format);

CREATE INDEX ix_datasets_status
    ON datasets(status);


CREATE TABLE variables (
    variable_id UUID PRIMARY KEY,
    variable_key VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(300) NOT NULL,
    inferred_type VARCHAR(50) NOT NULL,
    unit VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_variables_name
    ON variables(name);


CREATE TABLE dataset_variables (
    dataset_variable_id UUID PRIMARY KEY,
    dataset_id UUID NOT NULL
        REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    variable_id UUID NOT NULL
        REFERENCES variables(variable_id) ON DELETE CASCADE,
    original_name VARCHAR(300) NOT NULL,
    column_position INTEGER NOT NULL,
    non_null_count INTEGER NOT NULL,
    missing_count INTEGER NOT NULL,
    missing_percentage DOUBLE PRECISION NOT NULL,
    unique_count INTEGER NOT NULL,
    sample_values JSONB NOT NULL DEFAULT '[]'::jsonb,
    statistics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_dataset_variable
        UNIQUE (dataset_id, variable_id)
);

CREATE INDEX ix_dataset_variables_dataset_id
    ON dataset_variables(dataset_id);

CREATE INDEX ix_dataset_variables_variable_id
    ON dataset_variables(variable_id);

CREATE INDEX ix_dataset_variables_dataset_position
    ON dataset_variables(dataset_id, column_position);