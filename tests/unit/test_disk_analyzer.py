from fixos.diagnostics.disk_analyzer import DiskAnalyzer


def test_cleanup_suggestions_are_age_bounded_and_do_not_prune_docker_volumes():
    analyzer = DiskAnalyzer()
    suggestions = analyzer.suggest_cleanup_actions(
        analyzer.base_path,
        cache_dirs=[
            {
                "path": "/tmp/cache with spaces",
                "size_mb": 101,
                "size_gb": 0.1,
                "cache_type": "npm",
            }
        ],
        log_dirs=[
            {
                "path": "/tmp/logs with spaces",
                "size_mb": 101,
                "size_gb": 0.1,
            }
        ],
        temp_dirs=[
            {
                "path": "/tmp/temp with spaces",
                "size_mb": 101,
                "size_gb": 0.1,
                "temp_type": "system_temp",
            }
        ],
        large_files=[],
    )

    by_type = {item["type"]: item for item in suggestions}
    assert "--volumes" not in by_type["docker_cleanup"]["command"]
    assert "-mtime +7" in by_type["cache_cleanup"]["command"]
    assert "rm -rf" not in by_type["cache_cleanup"]["command"]
    assert "-mtime +30" in by_type["log_cleanup"]["command"]
    assert "rm -rf" not in by_type["temp_cleanup"]["command"]


def test_cleanup_suggestion_paths_are_shell_quoted():
    analyzer = DiskAnalyzer()
    suggestions = analyzer.suggest_cleanup_actions(
        analyzer.base_path,
        cache_dirs=[
            {
                "path": "/tmp/cache; touch SHOULD_NOT_RUN",
                "size_mb": 101,
                "size_gb": 0.1,
                "cache_type": "npm",
            }
        ],
        log_dirs=[],
        temp_dirs=[],
        large_files=[],
    )

    command = next(item["command"] for item in suggestions if item["type"] == "cache_cleanup")
    assert "'" in command
