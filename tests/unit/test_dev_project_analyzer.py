from fixos.diagnostics.dev_project_analyzer import DevProjectAnalyzer


def test_target_recreate_command_matches_project_ecosystem(tmp_path, monkeypatch):
    monkeypatch.setattr(DevProjectAnalyzer, "_get_dir_size", lambda self, path: 1)
    analyzer = DevProjectAnalyzer(str(tmp_path))

    rust = tmp_path / "rust"
    (rust / "target").mkdir(parents=True)
    (rust / "Cargo.toml").touch()
    java = tmp_path / "java"
    (java / "target").mkdir(parents=True)
    (java / "pom.xml").touch()

    assert (
        analyzer._check_dependency_folder(rust / "target").recreate_command
        == "cargo build"
    )
    assert (
        analyzer._check_dependency_folder(java / "target").recreate_command
        == "mvn install"
    )


def test_vendor_recreate_command_matches_go_and_php(tmp_path, monkeypatch):
    monkeypatch.setattr(DevProjectAnalyzer, "_get_dir_size", lambda self, path: 1)
    analyzer = DevProjectAnalyzer(str(tmp_path))

    go = tmp_path / "go"
    (go / "vendor").mkdir(parents=True)
    (go / "go.mod").touch()
    php = tmp_path / "php"
    (php / "vendor").mkdir(parents=True)
    (php / "composer.json").touch()

    assert (
        analyzer._check_dependency_folder(go / "vendor").recreate_command
        == "go mod vendor"
    )
    assert (
        analyzer._check_dependency_folder(php / "vendor").recreate_command
        == "composer install"
    )


def test_glob_indicator_marks_dotnet_artifact_as_recreatable(tmp_path, monkeypatch):
    monkeypatch.setattr(DevProjectAnalyzer, "_get_dir_size", lambda self, path: 1)
    analyzer = DevProjectAnalyzer(str(tmp_path))
    project = tmp_path / "dotnet"
    (project / "bin").mkdir(parents=True)
    (project / "demo.csproj").touch()

    dependency = analyzer._check_dependency_folder(project / "bin")

    assert dependency.can_recreate is True
    assert dependency.recreate_command == "dotnet build"
