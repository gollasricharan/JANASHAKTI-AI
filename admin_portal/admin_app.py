
import sys
import runpy
from pathlib import Path

# Main project directory
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Allow imports from the main project
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Admin-only dashboard
ADMIN_DASHBOARD = (
    PROJECT_DIR / "admin_portal" / "admin_dashboard.py"
)

if not ADMIN_DASHBOARD.is_file():
    raise FileNotFoundError(
        f"Admin Dashboard not found: {ADMIN_DASHBOARD}"
    )

# Run administrator dashboard
runpy.run_path(
    str(ADMIN_DASHBOARD),
    run_name="__main__"
)
