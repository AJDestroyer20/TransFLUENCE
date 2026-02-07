"""
FL Studio → TransProj Parser (PyFLP-backed)

Best-effort parsing of channels, patterns, playlist, and notes.
"""

import logging
from pathlib import Path

from core.transproj import TransProj, Track, Clip, Note, Plugin

logger = logging.getLogger(__name__)

try:
    from pyflp import Project  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Project = None


class FLStudioParser:
    """Parse FL Studio .flp files into TransProj using PyFLP."""

    def parse(self, filepath: str) -> TransProj:
        if Project is None:
            raise ImportError("pyflp is required to parse FL Studio projects")

        project = self._load_project(filepath)
        transproj = TransProj(
            name=Path(filepath).stem,
            tempo=getattr(project, "tempo", 120.0),
            ppq=960,
        )

        channels = getattr(project, "channels", [])
        for channel in channels:
            track = Track(
                name=getattr(channel, "name", "Channel"),
                volume=getattr(channel, "volume", 1.0),
                pan=getattr(channel, "pan", 0.0),
            )

            plugin_name = None
            if hasattr(channel, "plugin"):
                plugin_obj = getattr(channel, "plugin")
                plugin_name = getattr(plugin_obj, "name", None) or getattr(channel, "plugin", None)
            if plugin_name:
                track.instrument = Plugin(name=str(plugin_name), manufacturer="Image-Line", is_instrument=True)

            transproj.tracks.append(track)

        patterns = list(getattr(project, "patterns", []))
        pattern_map = {getattr(pattern, "id", idx + 1): pattern for idx, pattern in enumerate(patterns)}

        playlist = getattr(project, "playlist", None)
        if playlist:
            items = getattr(playlist, "items", playlist)
        else:
            items = []

        for item in items:
            pattern_id = getattr(item, "pattern", None)
            if hasattr(pattern_id, "id"):
                pattern_id = pattern_id.id
            pattern = pattern_map.get(pattern_id)
            if not pattern:
                continue

            track_idx = getattr(item, "track", 0)
            if hasattr(track_idx, "index"):
                track_idx = track_idx.index
            if not (0 <= track_idx < len(transproj.tracks)):
                continue

            clip = Clip(
                name=getattr(pattern, "name", f"Pattern {pattern_id}"),
                start=float(getattr(item, "position", 0)) / transproj.ppq,
                duration=float(getattr(item, "length", 0)) / transproj.ppq,
                is_midi=True,
            )

            notes = getattr(pattern, "notes", [])
            for note in notes:
                clip.notes.append(
                    Note(
                        position=float(getattr(note, "position", 0)) / transproj.ppq,
                        duration=float(getattr(note, "length", 0)) / transproj.ppq,
                        key=int(getattr(note, "key", 60)),
                        velocity=float(getattr(note, "velocity", 100)) / 127.0,
                    )
                )

            transproj.tracks[track_idx].clips.append(clip)

        logger.info(
            "✓ Parsed %s tracks, %s clips, %s notes",
            len(transproj.tracks),
            transproj.total_clips(),
            transproj.total_notes(),
        )
        return transproj

    def _load_project(self, filepath: str):
        if hasattr(Project, "from_file"):
            return Project.from_file(filepath)
        if hasattr(Project, "load"):
            return Project.load(filepath)
        return Project(filepath)


def parse_flstudio_project(filepath: str) -> TransProj:
    """Convenience function to parse FL Studio project."""
    parser = FLStudioParser()
    return parser.parse(filepath)


__all__ = ["FLStudioParser", "parse_flstudio_project"]
