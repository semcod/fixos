"""
Global constants for fixOS - avoiding magic numbers.
"""

# Session timeouts
DEFAULT_SESSION_TIMEOUT = 300  # 5 minutes
HITL_TIMEOUT_BUFFER = 80  # Buffer time for HITL session (seconds)
AUTONOMOU_TIMEOUT_BUFFER = 40  # Buffer time for autonomous session
CLEANUP_TIMEOUT_ESTIMATE = 120  # Estimated cleanup timeout
DEFAULT_COMMAND_TIMEOUT = 300  # Default command timeout in HITL session
LONG_COMMAND_TIMEOUT = 1800  # Long-running operations like system updates
FAST_COMMAND_TIMEOUT = 60  # Read-only and quick diagnostic commands
DIAGNOSTIC_CMD_TIMEOUT = 20  # Timeout for quick diagnostic shell commands

# String lengths / limits
MAX_COMMAND_LENGTH = 200  # Maximum length for command display
MAX_SEARCH_QUERY_LENGTH = 500  # Maximum length for search query
MAX_OUTPUT_LINES = 40  # Maximum output lines to display
MAX_OUTPUT_PREVIEW_LENGTH = 1000  # Maximum length for output preview
MAX_ANON_PREVIEW_LENGTH = 800  # Maximum length for anonymized preview
MAX_STDERR_PREVIEW_LENGTH = 300  # Maximum length for stderr preview
MAX_DIRECT_CMD_PREVIEW_LENGTH = 600  # Maximum length for direct command preview in chat
MAX_TECH_TERMS = 4  # Maximum tech terms to extract for search topic
HOSTNAME_DISPLAY_LENGTH = 65  # Length for hostname display
CONFIG_DISPLAY_LENGTH = 40  # Length for config line display
PROFILE_DISPLAY_LENGTH = 55  # Length for profile display
DIVIDER_LENGTH = 60  # Default divider length
UI_BORDER_WIDTH = 65  # Border width for panels

# Token/API limits
DEFAULT_TOKEN_LIMIT = 2000  # Default token estimate
MAX_WEB_SEARCH_COUNT = 5  # Maximum web searches per session

# Service/process limits
DEFAULT_HISTORY_LIMIT = 20  # Default history items to show
MAX_FIXES_DEFAULT = 10  # Default maximum number of fixes per session
SERVICE_SCAN_THRESHOLD_MB = 500  # Default threshold for service data scan
SIZE_THRESHOLD_GB_DEFAULT = 1.0  # Default size threshold for cleanup items in GB

# Text formatting
COMMAND_PREFIX_LENGTH = 80  # Max length for command prefix in output
MAX_SUMMARY_LENGTH = 200  # Max summary chars for derived search topic

# Disk / Resource thresholds
DISK_USAGE_CRITICAL = 95
DISK_USAGE_WARNING = 85
DISK_USAGE_MODERATE = 70
MAX_LARGE_FILES_DEFAULT = 20
MAX_CACHE_DIRS_DEFAULT = 15
MAX_LOG_DIRS_DEFAULT = 10
MAX_TEMP_DIRS_DEFAULT = 10
MIN_FILE_SIZE_MB = 100
LARGE_FILE_SIZE_MB = 500
CACHE_SIZE_HIGH_MB = 500
CACHE_SIZE_MEDIUM_MB = 100

# Resource/Process limits
MAX_TOP_PROCESSES = 10
MAX_AUTOSTART_SERVICES = 30
MAX_USER_AUTOSTART = 20
MAX_SLOW_SERVICES = 15
MAX_NETWORK_INTERFACES = 10

# Security diagnostic limits
MAX_OPEN_PORTS = 30
MAX_SECURITY_LOGS = 20
MAX_AUTH_FAILURES = 10
MAX_NETWORK_INTERFACES_DIAG = 20
MAX_SUDO_USERS = 5
MAX_SUID_FILES = 15

# Audio diagnostic limits
MAX_AUDIO_STATUS_LINES = 20
MAX_AUDIO_RESULTS = 30

# Flatpak diagnostic limits
FLATPAK_BLOAT_RATIO_CRITICAL = 2.5
FLATPAK_BLOAT_RATIO_NORMAL = 1.5
MAX_DUPLICATE_APPS_SHOW = 3
MAX_LARGE_APPS_SHOW = 5
FLATPAK_LEFTOVER_THRESHOLD_MB = 50

# Dev project diagnostic limits
DEV_PROJECT_MAX_DEPTH = 5
DEV_PROJECT_MIN_SIZE_MB = 100
DEV_PROJECT_OLD_DAYS = 30

# Storage diagnostic limits
MIN_DNF_CACHE_MB = 10
MIN_JOURNAL_LOG_MB = 100
MIN_DOCKER_DANGLING_MB = 50
MIN_PODMAN_MB = 500
MIN_BROWSER_CACHE_MB = 100
MIN_BTRFS_SNAPSHOT_SIZE_GB = 1
MIN_COREDUMP_MB = 100
MIN_DEBUGINFO_MB = 500
MIN_ORPHANED_PACKAGES = 5
MIN_HOME_LARGE_FILE_MB = 200
MIN_HOME_LARGE_DIR_MB = 500
DEFAULT_CLEANUP_THRESHOLD_MB = 500
GENERIC_CACHE_THRESHOLD_MB = 1024
MAX_HOME_LARGE_FILES_DISPLAY = 30
MAX_HOME_LARGE_DIRS_DISPLAY = 20
MIN_STALE_DAYS = 90

# Developer project artifact scanner (venvs, node_modules, build caches, ...)
PROJECT_SCAN_DEFAULT_PATH = "~/github"
PROJECT_SCAN_THRESHOLD_MB = 50
PROJECT_SCAN_STALE_DAYS = 60
PROJECT_SCAN_MAX_DEPTH = 4

# Package / OS diagnostic limits
MAX_PKG_HISTORY = 5
MAX_LOG_ERRORS = 20
MAX_DMESG_ERRORS = 15

# Package environment diagnostic limits
MAX_ORPHANED_PACKAGES = 30
MAX_PKG_RECENTLY_INSTALLED = 25
MAX_PKG_LARGE_INSTALLED = 30
MAX_PKG_LEAF_UNUSED = 40
MAX_PKG_FLATPAK_UNUSED = 30

# File analysis diagnostic limits
MAX_FILE_ANALYSIS_LARGE = 30
MAX_FILE_ANALYSIS_DUPES = 25
MAX_FILE_ANALYSIS_MEDIA = 20
MIN_LARGE_FILE_ANALYSIS_MB = 200
