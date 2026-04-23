from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .image_detector import ImageDetector
from .image_methods import CopyMoveMethod, ELAMethod, ExifMethod, LLMMethod, URNMethod
from .minimal_baseline import TrainableBaselineMethod
from .service_errors import ValidationError


DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "config" / "model_registry.json"


@dataclass(slots=True)
class MethodConfig:
    kind: str
    enabled: bool = True
    name: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ImageProfileConfig:
    name: str
    model_version: str
    methods: list[MethodConfig] = field(default_factory=list)

    @property
    def enabled_methods(self) -> list[MethodConfig]:
        return [method for method in self.methods if method.enabled]


class DetectionModelRegistry:
    def __init__(
        self,
        *,
        version: str,
        default_image_profile: str,
        image_profiles: dict[str, ImageProfileConfig],
        config_path: Path,
        config_mtime_ns: int,
    ) -> None:
        self.version = version
        self.default_image_profile = default_image_profile
        self.image_profiles = image_profiles
        self.config_path = config_path
        self.config_mtime_ns = config_mtime_ns
        self._image_detectors: dict[str, ImageDetector] = {}

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "DetectionModelRegistry":
        resolved_path = cls._resolve_config_path(config_path)
        try:
            payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValidationError(f"model registry config not found: {resolved_path}") from exc
        except json.JSONDecodeError as exc:
            raise ValidationError(f"model registry config is not valid JSON: {resolved_path}") from exc

        version = str(payload.get("registry_version") or "image-model-registry-v1")
        default_image_profile = str(payload.get("default_image_profile") or "").strip()
        image_profiles_raw = payload.get("image_profiles")
        if not isinstance(image_profiles_raw, list) or not image_profiles_raw:
            raise ValidationError("model registry config must define image_profiles")

        image_profiles: dict[str, ImageProfileConfig] = {}
        for item in image_profiles_raw:
            profile = cls._parse_image_profile(item)
            if profile.name in image_profiles:
                raise ValidationError(f"duplicate image profile '{profile.name}' in model registry")
            image_profiles[profile.name] = profile

        if not default_image_profile:
            default_image_profile = next(iter(image_profiles))
        if default_image_profile not in image_profiles:
            raise ValidationError(f"default image profile '{default_image_profile}' is not defined")

        return cls(
            version=version,
            default_image_profile=default_image_profile,
            image_profiles=image_profiles,
            config_path=resolved_path,
            config_mtime_ns=resolved_path.stat().st_mtime_ns,
        )

    @staticmethod
    def _resolve_config_path(config_path: str | Path | None) -> Path:
        if config_path is not None:
            return Path(config_path)
        env_path = os.getenv("AI_MODEL_REGISTRY_PATH", "").strip()
        if env_path:
            return Path(env_path)
        return DEFAULT_REGISTRY_PATH

    @classmethod
    def _parse_image_profile(cls, payload: Any) -> ImageProfileConfig:
        if not isinstance(payload, dict):
            raise ValidationError("image profile entries must be objects")

        profile_name = str(payload.get("name") or "").strip()
        if not profile_name:
            raise ValidationError("image profile is missing name")

        model_version = str(payload.get("model_version") or "").strip()
        if not model_version:
            raise ValidationError(f"image profile '{profile_name}' is missing model_version")

        methods_raw = payload.get("methods")
        if not isinstance(methods_raw, list) or not methods_raw:
            raise ValidationError(f"image profile '{profile_name}' must define methods")

        methods = [cls._parse_method_config(profile_name, item) for item in methods_raw]
        return ImageProfileConfig(name=profile_name, model_version=model_version, methods=methods)

    @staticmethod
    def _parse_method_config(profile_name: str, payload: Any) -> MethodConfig:
        if not isinstance(payload, dict):
            raise ValidationError(f"image profile '{profile_name}' contains a non-object method entry")

        kind = str(payload.get("kind") or "").strip()
        if not kind:
            raise ValidationError(f"image profile '{profile_name}' contains a method without kind")

        enabled = bool(payload.get("enabled", True))
        name = payload.get("name")
        if name is not None:
            name = str(name).strip() or None
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            raise ValidationError(
                f"image profile '{profile_name}' method '{kind}' must use an object for params"
            )
        return MethodConfig(kind=kind, enabled=enabled, name=name, params=params)

    def resolve_image_profile(self, profile_name: str | None) -> ImageProfileConfig:
        resolved_name = (profile_name or self.default_image_profile).strip()
        try:
            return self.image_profiles[resolved_name]
        except KeyError as exc:
            raise ValidationError(f"unknown image model profile: {resolved_name}") from exc

    def build_image_detector(self, profile_name: str | None = None) -> ImageDetector:
        profile = self.resolve_image_profile(profile_name)
        if profile.name not in self._image_detectors:
            methods = [self._build_method(method) for method in profile.enabled_methods]
            self._image_detectors[profile.name] = ImageDetector(methods=methods)
        return self._image_detectors[profile.name]

    def image_profile_names(self) -> list[str]:
        return sorted(self.image_profiles.keys())

    def describe_image_profiles(self) -> dict[str, dict[str, Any]]:
        return {
            profile_name: {
                "model_version": profile.model_version,
                "enabled_methods": [self._display_method_name(method) for method in profile.enabled_methods],
            }
            for profile_name, profile in sorted(self.image_profiles.items())
        }

    def describe_image_profile(self, profile_name: str | None) -> dict[str, Any]:
        profile = self.resolve_image_profile(profile_name)
        return {
            "name": profile.name,
            "model_version": profile.model_version,
            "enabled_methods": [self._display_method_name(method) for method in profile.enabled_methods],
            "methods": [
                {
                    "kind": method.kind,
                    "name": method.name,
                    "enabled": method.enabled,
                    "params": dict(method.params),
                }
                for method in profile.methods
            ],
        }

    def metadata(self) -> dict[str, Any]:
        return {
            "registry_version": self.version,
            "registry_path": str(self.config_path),
            "config_mtime_ns": self.config_mtime_ns,
            "config_mtime": datetime.fromtimestamp(
                self.config_mtime_ns / 1_000_000_000,
                tz=timezone.utc,
            ).isoformat(),
            "default_image_profile": self.default_image_profile,
            "available_image_profiles": self.image_profile_names(),
        }

    @staticmethod
    def _display_method_name(method: MethodConfig) -> str:
        if method.kind in {"urn", "baseline_classifier"} and method.name:
            return method.name
        return method.kind

    def _build_method(self, method: MethodConfig):
        if method.kind == "llm":
            return LLMMethod()
        if method.kind == "ela":
            return ELAMethod()
        if method.kind == "exif":
            return ExifMethod()
        if method.kind == "cmd":
            return CopyMoveMethod()
        if method.kind == "urn":
            method_name = method.name or str(method.params.get("name") or "").strip()
            weight_path = str(method.params.get("weight_path") or "").strip()
            if not method_name or not weight_path:
                raise ValidationError("urn method config requires name and params.weight_path")
            return URNMethod(method_name, weight_path)
        if method.kind == "baseline_classifier":
            method_name = method.name or str(method.params.get("name") or "").strip()
            model_path = str(method.params.get("model_path") or "").strip()
            if not method_name or not model_path:
                raise ValidationError("baseline_classifier method config requires name and params.model_path")
            return TrainableBaselineMethod(method_name, self._resolve_path(model_path))
        raise ValidationError(f"unsupported method kind in registry: {method.kind}")

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return (self.config_path.parent / path).resolve()
