ALTER TABLE files
ADD COLUMN storage_backend VARCHAR(30) NOT NULL DEFAULT 'local';

ALTER TABLE files
ADD COLUMN storage_key TEXT;

-- Retain the old path temporarily for backward compatibility.
ALTER TABLE files
ALTER COLUMN storage_path DROP NOT NULL;

CREATE UNIQUE INDEX uq_files_storage_key
ON files (storage_key)
WHERE storage_key IS NOT NULL;

CREATE INDEX ix_files_storage_backend
ON files (storage_backend);