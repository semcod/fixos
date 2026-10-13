"""Container storage analyzers (Docker, Podman)."""

from __future__ import annotations

import os
from typing import ClassVar

from fixos.constants import MIN_DOCKER_DANGLING_MB, MIN_PODMAN_MB
from fixos.diagnostics.storage_analyzer import StorageItem


class _ContainerAnalyzerMixin:
    """Mixin providing container _analyze_* methods for StorageAnalyzer."""

    _DOCKER_DF_SECTIONS: ClassVar[dict[str, str]] = {
        "Images space usage:": "images",
        "Containers space usage:": "containers",
        "Local Volumes space usage:": "volumes",
        "Build Cache": "build_cache",
    }

    @staticmethod
    def _detect_docker_section(line: str) -> str | None:
        """Return the section name if *line* is a section header, else None."""
        for prefix, section in _ContainerAnalyzerMixin._DOCKER_DF_SECTIONS.items():
            if line.startswith(prefix):
                return section
        return None

    @staticmethod
    def _parse_docker_df_output(output: str) -> dict:
        """Parse 'docker system df -v' output into image/cache stats."""
        from fixos.diagnostics.storage_analyzer import StorageAnalyzer

        total_images = 0
        dangling_images = 0
        dangling_size = 0
        build_cache = 0
        current_section = None

        for raw_line in output.split("\n"):
            line = raw_line.strip()
            section = _ContainerAnalyzerMixin._detect_docker_section(line)
            if section:
                current_section = section
                continue
            if (
                current_section == "images"
                and line
                and not line.startswith("REPOSITORY")
            ):
                parts = line.split()
                if len(parts) >= 4:
                    if parts[0] == "<none>" or parts[1] == "<none>":
                        dangling_images += 1
                        dangling_size += StorageAnalyzer._parse_size_static(parts[3])
                    total_images += 1
            elif (
                current_section == "build_cache"
                and line
                and not line.startswith("CACHE ID")
            ):
                parts = line.split()
                if len(parts) >= 2:
                    build_cache += StorageAnalyzer._parse_size_static(parts[-2])

        return {
            "total_images": total_images,
            "dangling_images": dangling_images,
            "dangling_size": dangling_size,
            "build_cache": build_cache,
        }

    def _add_dangling_images_item(
        self, dangling_images: int, dangling_size: int
    ) -> None:
        """Append a StorageItem for dangling Docker images if threshold exceeded."""
        if dangling_size > MIN_DOCKER_DANGLING_MB * 1024 * 1024:
            self.items.append(
                StorageItem(
                    name=f"Dangling Docker Images ({dangling_images})",
                    path="/var/lib/docker",
                    size_bytes=dangling_size,
                    category="containers",
                    risk="low",
                    cleanup_command="docker image prune -f",
                    description=(
                        f"Dangling images (bez tagu): {StorageItem._format_size(dangling_size)}. "
                        "Bezpieczne do usunięcia - to nieużywane obrazy."
                    ),
                )
            )

    def _add_build_cache_item(self, build_cache: int) -> None:
        """Append a StorageItem for Docker build cache if threshold exceeded."""
        if build_cache > 100 * 1024 * 1024:
            self.items.append(
                StorageItem(
                    name="Docker Build Cache",
                    path="/var/lib/docker",
                    size_bytes=build_cache,
                    category="containers",
                    risk="low",
                    cleanup_command="docker builder prune -f",
                    description=(
                        f"Build cache Dockera: {StorageItem._format_size(build_cache)}. "
                        "Bezpieczne do usunięcia."
                    ),
                )
            )

    def _add_docker_total_item(self, total_images: int, dangling_images: int) -> None:
        """Append a StorageItem for total Docker usage if threshold exceeded."""
        total_docker = self._get_dir_size("/var/lib/docker")
        if total_docker > 1024**3:
            self.items.append(
                StorageItem(
                    name="Docker Total",
                    path="/var/lib/docker",
                    size_bytes=total_docker,
                    category="containers",
                    risk="medium",
                    # Never a bulk volume prune: volumes are data and are
                    # chosen one by one with `fixos cleanup --docker-volumes`.
                    cleanup_command="docker builder prune --force --filter until=168h",
                    description=(
                        f"Docker łącznie: {StorageItem._format_size(total_docker)}. "
                        f"Obrazy: {total_images}, dangling: {dangling_images}. "
                        "Czyści cache buildów starszy niż 7 dni; wolumeny wybierz "
                        "ręcznie przez `fixos cleanup --docker-volumes`."
                    ),
                )
            )

    def _analyze_docker(self):
        """Analyze Docker storage - images, containers, volumes, build cache"""
        if not os.path.exists("/var/lib/docker"):
            return

        output = self._run_command(["docker", "system", "df", "-v"])
        if not output:
            size = self._get_dir_size("/var/lib/docker")
            if size > 500 * 1024 * 1024:
                self.items.append(
                    StorageItem(
                        name="Docker",
                        path="/var/lib/docker",
                        size_bytes=size,
                        category="containers",
                        risk="medium",
                        cleanup_command="docker system prune -a",
                        description=f"Docker zajmuje {StorageItem._format_size(size)}. "
                        "Uwaga: usunie nieużywane obrazy i kontenery.",
                    )
                )
            return

        stats = self._parse_docker_df_output(output)
        self._add_dangling_images_item(stats["dangling_images"], stats["dangling_size"])
        self._add_build_cache_item(stats["build_cache"])
        self._add_docker_total_item(stats["total_images"], stats["dangling_images"])

    def _analyze_podman(self):
        """Analyze Podman storage"""
        if not os.path.exists("/var/lib/containers"):
            return

        size = self._get_dir_size("/var/lib/containers")
        if size > MIN_PODMAN_MB * 1024 * 1024:
            self.items.append(
                StorageItem(
                    name="Podman",
                    path="/var/lib/containers",
                    size_bytes=size,
                    category="containers",
                    risk="medium",
                    cleanup_command="podman system prune -a",
                    description=f"Podman zajmuje {StorageItem._format_size(size)}.",
                )
            )
