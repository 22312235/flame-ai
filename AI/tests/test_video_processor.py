import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import tempfile

from ingestion.video_processor import (
    extract_video_metadata,
    extract_video_frames,
    extract_video_audio,
    transcribe_video_audio,
    detect_video_scenes,
    extract_scene_keyframes,
    process_video
)


class TestVideoProcessor(unittest.TestCase):

    @patch("ingestion.video_processor.subprocess.run")
    def test_extract_video_metadata(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 320,
                        "height": 240,
                        "avg_frame_rate": "10/1",
                        "nb_frames": "100"
                    },
                    {
                        "codec_type": "audio",
                        "codec_name": "aac"
                    }
                ],
                "format": {"duration": "10.0"}
            }),
            stderr=""
        )

        with tempfile.NamedTemporaryFile(suffix=".mp4") as video:
            result = extract_video_metadata(video.name)

        self.assertEqual(result["width"], 320)
        self.assertEqual(result["height"], 240)
        self.assertEqual(result["fps"], 10.0)
        self.assertTrue(result["has_audio"])
    @patch("ingestion.video_processor.subprocess.run")
    def test_metadata_handles_invalid_fps(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 320,
                        "height": 240,
                        "avg_frame_rate": "N/A",
                        "nb_frames": "100"
                    }
                ],
                "format": {"duration": "10.0"}
            }),
            stderr=""
        )

        with tempfile.NamedTemporaryFile(suffix=".mp4") as video:
            result = extract_video_metadata(video.name)

        self.assertEqual(result["fps"], 0)
    def test_missing_video_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            extract_video_metadata("missing_video.mp4")

        
    def test_transcription_reads_json_lines(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "speech.wav"
            audio_path.touch()

            output_path = Path(temp_dir) / "transcript.json"

            transcript_data = [
                {"start": 0, "end": 1000, "text": "Hello"},
                {"start": 1000, "end": 2000, "text": "World"}
            ]

            def create_transcript(*args, **kwargs):
                output_path.write_text(
                    "\n".join(json.dumps(item) for item in transcript_data),
                    encoding="utf-8"
                )
                return MagicMock(returncode=0, stderr="")

            with patch(
                "ingestion.video_processor.subprocess.run",
                side_effect=create_transcript
            ):
                result = transcribe_video_audio(
                    str(audio_path),
                    str(output_path)
                )

            self.assertEqual(len(result["transcript"]), 2)
            self.assertEqual(result["transcript"][0]["text"], "Hello")
            self.assertEqual(result["transcript"][1]["text"], "World")
    @patch("ingestion.video_processor.extract_scene_keyframes")
    @patch("ingestion.video_processor.detect_video_scenes")
    @patch("ingestion.video_processor.extract_video_frames")
    @patch("ingestion.video_processor.extract_video_metadata")
    def test_process_video_without_audio(
        self, mock_metadata, mock_frames, mock_scenes, mock_keyframes
    ):
        mock_metadata.return_value = {
            "has_audio": False,
            "file_name": "test_no_audio.mp4"
        }

        mock_frames.return_value = [
            {
                "frame_id": "frame_0.00s.jpg",
                "timestamp_seconds": 0.0
            }
        ]
        mock_scenes.return_value = [
            {
                "timestamp_seconds": 3.0,
                "source": "test_no_audio.mp4"
            }
        ]

        mock_keyframes.return_value = [
            {
                "frame_id": "scene_1_3.00s.jpg",
                "timestamp_seconds": 3.0,
                "source": "test_no_audio.mp4"
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".mp4") as video:
            result = process_video(video.name)

        self.assertIsNone(result["audio"])
        self.assertIsNone(result["transcription"])
        self.assertEqual(
            result["warnings"],
            ["Video has no audio stream."]
        )
        self.assertEqual(len(result["frames"]), 1)
        mock_metadata.assert_called_once()
        mock_frames.assert_called_once()
        self.assertEqual(len(result["scenes"]), 1)
        self.assertEqual(len(result["scene_keyframes"]), 1)

        mock_scenes.assert_called_once()
        mock_keyframes.assert_called_once()
        
    @patch("ingestion.video_processor.extract_video_metadata")
    @patch("ingestion.video_processor.subprocess.run")
    def test_extract_video_frames(
        self, mock_run, mock_metadata
    ):
        mock_metadata.return_value = {
            "duration_seconds": 5.0
        }

        def create_frame(command, **kwargs):
            Path(command[-1]).touch()
            return MagicMock(returncode=0, stderr="")

        mock_run.side_effect = create_frame

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "test.mp4"
            video_path.touch()

            result = extract_video_frames(
                str(video_path),
                interval_seconds=2
            )

        self.assertEqual(len(result), 3)
        self.assertEqual(
            [frame["timestamp_seconds"] for frame in result],
            [0.0, 2.0, 4.0]
        )
        self.assertTrue(
            all(frame["source"] == "test.mp4" for frame in result)
        )
    @patch("ingestion.video_processor.extract_video_metadata")
    @patch("ingestion.video_processor.subprocess.run")
    def test_extract_video_audio(
        self, mock_run, mock_metadata
    ):
        mock_metadata.return_value = {
            "has_audio": True
        }

        mock_run.return_value = MagicMock(
            returncode=0,
            stderr=""
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "test.mp4"
            video_path.touch()

            output_path = Path(temp_dir) / "test_audio.wav"

            result = extract_video_audio(
                str(video_path),
                str(output_path)
            )

            self.assertEqual(result["audio_file"], "test_audio.wav")
            self.assertEqual(result["source"], "test.mp4")
            self.assertEqual(result["sample_rate"], 16000)
            self.assertEqual(result["channels"], 1)
            self.assertEqual(result["format"], "wav")

            mock_run.assert_called_once()
    @patch("ingestion.video_processor.subprocess.run")
    def test_metadata_estimates_missing_frame_count(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "streams": [
                    {
                        "codec_type": "video",
                        "codec_name": "h264",
                        "width": 320,
                        "height": 240,
                        "avg_frame_rate": "30/1",
                        "nb_frames": "N/A"
                    }
                ],
                "format": {"duration": "10.0"}
            }),
            stderr=""
        )

        with tempfile.NamedTemporaryFile(suffix=".mp4") as video:
            result = extract_video_metadata(video.name)

        self.assertEqual(result["frame_count"], 300)
    @patch("ingestion.video_processor.subprocess.run")
    def test_detect_video_scenes_returns_empty_list(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr=""
        )

        with tempfile.NamedTemporaryFile(suffix=".mp4") as video:
            result = detect_video_scenes(video.name)

        self.assertEqual(result, [])
@patch("ingestion.video_processor.subprocess.run")
def test_detect_video_scenes(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr="[Parsed_showinfo_1] n: 0 pts: 30720 pts_time:3 duration:1024"
        )

        with tempfile.NamedTemporaryFile(suffix=".mp4") as video:
            result = detect_video_scenes(video.name)

        self.assertEqual(
            result,
            [{
                "timestamp_seconds": 3.0,
                "source": Path(video.name).name
            }]
        )        