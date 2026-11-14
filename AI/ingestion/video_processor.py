
import json
import subprocess
from pathlib import Path


def extract_video_metadata(file_path: str) -> dict:
    """Extract video and audio metadata using FFprobe."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    command = [
        "ffprobe",
        "-v", "error",
        "-show_streams",
        "-show_format",
        "-of", "json",
        str(path)
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        data = json.loads(result.stdout)

    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            f"FFprobe failed: {error.stderr}"
        ) from error

    except json.JSONDecodeError as error:
        raise RuntimeError("Invalid FFprobe output.") from error

    video_stream = next(
        (
            stream for stream in data.get("streams", [])
            if stream.get("codec_type") == "video"
        ),
        None
    )

    audio_stream = next(
        (
            stream for stream in data.get("streams", [])
            if stream.get("codec_type") == "audio"
        ),
        None
    )

    if video_stream is None:
        raise ValueError("No video stream found in the file.")

    format_info = data.get("format", {})
    duration = float(format_info.get("duration", 0))

    fps = video_stream.get("avg_frame_rate", "0/1")

    try:
       numerator, denominator = map(int, fps.split("/"))
       frame_rate = numerator / denominator if denominator else 0
    except (ValueError, AttributeError):
       frame_rate = 0

    return {
        "file_name": path.name,
        "file_size": path.stat().st_size,
        "duration_seconds":duration,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "fps": round(frame_rate, 3),
        "frame_count": (
            int(video_stream["nb_frames"])
            if video_stream.get("nb_frames", "").isdigit()
            else round(duration * frame_rate)
      ),
        "video_codec": video_stream.get("codec_name"),
        "audio_codec": (
            audio_stream.get("codec_name")
            if audio_stream else None
        ),
        "has_audio": audio_stream is not None
    }

def extract_video_frames(
    file_path: str,
    output_dir: str = None,
    interval_seconds: float = 5.0
) -> list:
    """Extract video frames at regular timestamp intervals."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    if interval_seconds <= 0:
        raise ValueError("Frame interval must be greater than zero.")

    if output_dir is None:
        output_dir = path.parent / f"{path.stem}_frames"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    metadata = extract_video_metadata(str(path))
    duration = metadata["duration_seconds"]

    frames = []
    timestamp = 0.0

    while timestamp < duration:
        frame_name = f"frame_{timestamp:.2f}s.jpg"
        frame_path = output_path / frame_name

        command = [
            "ffmpeg",
            "-y",
            "-ss", str(timestamp),
            "-i", str(path),
            "-frames:v", "1",
            "-q:v", "2",
            str(frame_path)
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and frame_path.exists():
            frames.append({
                "frame_id": frame_name,
                "path": str(frame_path),
                "timestamp_seconds": round(timestamp, 2),
                "source": path.name
            })

        timestamp += interval_seconds

    return frames
def detect_video_scenes(
    file_path: str,
    threshold: float = 0.1
) -> list:
    """Detect scene changes and return their timestamps."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    if not 0 < threshold <= 1:
        raise ValueError("Threshold must be between 0 and 1.")

    command = [
        "ffmpeg",
        "-i", str(path),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-an",
        "-f", "null",
        "-"
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Scene detection failed: {result.stderr}"
        )

    scenes = []

    for line in result.stderr.splitlines():
        if "pts_time:" in line:
            try:
                timestamp = float(
                    line.split("pts_time:")[1].split()[0]
                )
                scenes.append({
                    "timestamp_seconds": timestamp,
                    "source": path.name
                })
            except (ValueError, IndexError):
                continue

    return scenes
def extract_scene_keyframes(
    file_path: str,
    scenes: list = None
) -> list:
    """Extract one image for each detected scene change."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    if scenes is None:
        scenes = detect_video_scenes(str(path))

    output_dir = path.parent / f"{path.stem}_scene_frames"
    output_dir.mkdir(parents=True, exist_ok=True)

    keyframes = []

    for index, scene in enumerate(scenes, start=1):
        timestamp = scene["timestamp_seconds"]

        output_path = output_dir / f"scene_{index}_{timestamp:.2f}s.jpg"

        command = [
            "ffmpeg",
            "-y",
            "-ss", str(timestamp),
            "-i", str(path),
            "-frames:v", "1",
            str(output_path)
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Scene keyframe extraction failed: {result.stderr}"
            )

        keyframes.append({
            "frame_id": output_path.name,
            "path": str(output_path),
            "timestamp_seconds": timestamp,
            "source": path.name
        })

    return keyframes
def extract_video_audio(
    file_path: str,
    output_path: str = None
) -> dict:
    """Extract audio from a video and save it as a WAV file."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    metadata = extract_video_metadata(str(path))

    if not metadata["has_audio"]:
        raise ValueError("No audio stream found in the video.")

    if output_path is None:
        output_path = path.parent / f"{path.stem}_audio.wav"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i", str(path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(output_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Audio extraction failed: {result.stderr}"
        )

    return {
        "audio_file": output_path.name,
        "path": str(output_path),
        "source": path.name,
        "sample_rate": 16000,
        "channels": 1,
        "format": "wav"
    }
def transcribe_video_audio(
    audio_path: str,
    output_path: str = None,
    language: str = "auto"
) -> dict:
    """Transcribe audio using FFmpeg Whisper filter."""

    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(f"Audio not found: {path}")

    if output_path is None:
        output_path = path.parent / f"{path.stem}_transcript.json"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model_path = (
        Path(__file__).resolve().parents[2]
        / "models"
        / "ggml-tiny.bin"
    )

    if not model_path.exists():
        raise FileNotFoundError(
            f"Whisper model not found: {model_path}"
        )
    escaped_model_path = model_path.as_posix().replace(":", r"\\:")
    command = [
        "ffmpeg",
        "-y",
        "-i", str(path),
        "-af",
        (
            
            f"whisper=model={escaped_model_path}:"
            f"language={language}:"
            "use_gpu=false:"
            f"destination='{output_path.as_posix()}':"
            "format=json"
        ),
        "-f", "null",
        "-"
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Whisper transcription failed: {result.stderr}"
        )

    if not output_path.exists():
        raise RuntimeError(
            "Whisper completed but no transcript file was created."
        )

    transcript = []
    warnings = []

    if output_path.exists() and output_path.stat().st_size > 0:
        with open(output_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    transcript.append(json.loads(line))

    if not transcript:
        warnings.append("No speech detected or no transcript was generated.")
    return {
        "transcript_file": output_path.name,
        "path": str(output_path),
        "source": path.name,
        "language": language,
        "transcript": transcript,
        "warnings": warnings
    }
def process_video(
    file_path: str,
    frame_interval_seconds: float = 5.0,
    language: str = "auto"
) -> dict:
    """Run the complete video processing pipeline."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    # 1. Extract video metadata
    metadata = extract_video_metadata(str(path))

     # 2. Extract video frames at regular intervals
    frames = extract_video_frames(
        str(path),
        interval_seconds=frame_interval_seconds
    )

    # 3. Detect scene changes and extract scene keyframes
    scenes = detect_video_scenes(str(path))

    scene_keyframes = extract_scene_keyframes(
        str(path),
        scenes=scenes
    )

    warnings = []

    # 3. Extract audio and transcribe it
    audio = None
    transcription = None

    if metadata["has_audio"]:
        audio = extract_video_audio(str(path))

        transcription = transcribe_video_audio(
            audio["path"],
            language=language
        )

        warnings.extend(transcription.get("warnings", []))
    else:
        warnings.append("Video has no audio stream.")

    return {
        "source": path.name,
        "metadata": metadata,
        "frames": frames,
        "scenes": scenes,
        "scene_keyframes": scene_keyframes,
        "audio": audio,
        "transcription": transcription,
        "warnings": warnings
    }