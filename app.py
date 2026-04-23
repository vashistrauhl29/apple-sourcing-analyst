"""Entry-point shim for Streamlit Community Cloud.

The actual landing page lives in Overview.py. This file exists only because
the existing Streamlit Cloud deployment is configured with 'app.py' as its
main file path; executing Overview.py from here avoids having to reconfigure
the deployment.

For local development, prefer:  streamlit run Overview.py
"""
from pathlib import Path

_overview = Path(__file__).with_name("Overview.py")
exec(compile(_overview.read_text(), str(_overview), "exec"))
