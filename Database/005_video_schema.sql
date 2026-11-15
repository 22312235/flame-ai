-- ============================================================
-- Migration: 005_video_schema
-- Description: Creates video, frame, audio and transcript tables.
-- ============================================================


-- ============================================================
-- 1. VIDEOS
-- Stores technical metadata for each processed video.
-- One video record per original file.
-- ============================================================

CREATE TABLE videos (
    video_id UUID PRIMARY KEY,

    file_id UUID NOT NULL UNIQUE
        REFERENCES files(file_id)
        ON DELETE CASCADE,

    duration_seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,

    width INTEGER,
    height INTEGER,

    fps DOUBLE PRECISION NOT NULL DEFAULT 0.0,

    frame_count INTEGER NOT NULL DEFAULT 0,

    video_codec VARCHAR(100),
    audio_codec VARCHAR(100),

    has_audio BOOLEAN NOT NULL DEFAULT FALSE,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);


CREATE INDEX ix_videos_file_id
    ON videos(file_id);


-- ============================================================
-- 2. VIDEO FRAMES
-- Stores regular frames, detected scene events and keyframes.
--
-- frame_type values:
--   regular  : Frame extracted at a regular interval.
--   scene    : Detected scene-change timestamp.
--   keyframe : Image extracted at a scene-change timestamp.
-- ============================================================

CREATE TABLE video_frames (
    frame_id UUID PRIMARY KEY,

    video_id UUID NOT NULL
        REFERENCES videos(video_id)
        ON DELETE CASCADE,

    frame_type VARCHAR(30) NOT NULL,

    timestamp_seconds DOUBLE PRECISION NOT NULL,

    frame_file_id UUID
        REFERENCES files(file_id)
        ON DELETE SET NULL,

    frame_name VARCHAR(500),

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT ck_video_frames_type
        CHECK (
            frame_type IN ('regular', 'scene', 'keyframe')
        ),

    CONSTRAINT ck_video_frames_timestamp
        CHECK (timestamp_seconds >= 0)
);


CREATE INDEX ix_video_frames_video_id
    ON video_frames(video_id);

CREATE INDEX ix_video_frames_frame_file_id
    ON video_frames(frame_file_id);

CREATE INDEX ix_video_frames_timestamp
    ON video_frames(video_id, timestamp_seconds);

CREATE INDEX ix_video_frames_type
    ON video_frames(video_id, frame_type);


-- ============================================================
-- 3. AUDIO TRACKS
-- Stores metadata for audio extracted from a video.
-- A video can have zero or more audio tracks.
-- ============================================================

CREATE TABLE audio_tracks (
    audio_track_id UUID PRIMARY KEY,

    video_id UUID NOT NULL
        REFERENCES videos(video_id)
        ON DELETE CASCADE,

    audio_file_id UUID
        REFERENCES files(file_id)
        ON DELETE SET NULL,

    sample_rate INTEGER,
    channels INTEGER,

    audio_format VARCHAR(50),

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);


CREATE INDEX ix_audio_tracks_video_id
    ON audio_tracks(video_id);

CREATE INDEX ix_audio_tracks_audio_file_id
    ON audio_tracks(audio_file_id);


-- ============================================================
-- 4. TRANSCRIPTS
-- Stores transcription segments and associated metadata.
-- Transcripts belong to an extracted audio track.
-- ============================================================

CREATE TABLE transcripts (
    transcript_id UUID PRIMARY KEY,

    audio_track_id UUID NOT NULL
        REFERENCES audio_tracks(audio_track_id)
        ON DELETE CASCADE,

    transcript_file_id UUID
        REFERENCES files(file_id)
        ON DELETE SET NULL,

    language VARCHAR(50),

    segments JSONB NOT NULL DEFAULT '[]'::jsonb,

    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);


CREATE INDEX ix_transcripts_audio_track_id
    ON transcripts(audio_track_id);

CREATE INDEX ix_transcripts_transcript_file_id
    ON transcripts(transcript_file_id);