-- 004_image_schema.sql

CREATE TABLE images (
    image_id UUID PRIMARY KEY,
    file_id UUID NOT NULL UNIQUE,
    image_format VARCHAR(30) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    aspect_ratio DOUBLE PRECISION NOT NULL,
    pixel_count INTEGER NOT NULL,
    color_mode VARCHAR(30) NOT NULL,
    has_transparency BOOLEAN NOT NULL,
    frame_count INTEGER NOT NULL DEFAULT 1,
    exif_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    thumbnail_file_id UUID,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    processed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_images_file
        FOREIGN KEY (file_id)
        REFERENCES files(file_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_images_thumbnail_file
        FOREIGN KEY (thumbnail_file_id)
        REFERENCES files(file_id)
        ON DELETE SET NULL,

    CONSTRAINT ck_images_width_positive
        CHECK (width > 0),

    CONSTRAINT ck_images_height_positive
        CHECK (height > 0),

    CONSTRAINT ck_images_pixel_count_positive
        CHECK (pixel_count > 0),

    CONSTRAINT ck_images_frame_count_positive
        CHECK (frame_count > 0)
);

CREATE INDEX ix_images_file_id
    ON images(file_id);

CREATE INDEX ix_images_thumbnail_file_id
    ON images(thumbnail_file_id);


CREATE TABLE image_contexts (
    context_id UUID PRIMARY KEY,
    image_id UUID NOT NULL,
    document_unit_id UUID,
    context_type VARCHAR(50) NOT NULL DEFAULT 'standalone',
    context_label VARCHAR(300),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_image_contexts_image
        FOREIGN KEY (image_id)
        REFERENCES images(image_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_image_contexts_document_unit
        FOREIGN KEY (document_unit_id)
        REFERENCES document_units(unit_id)
        ON DELETE SET NULL
);

CREATE INDEX ix_image_contexts_image_id
    ON image_contexts(image_id);

CREATE INDEX ix_image_contexts_document_unit_id
    ON image_contexts(document_unit_id);