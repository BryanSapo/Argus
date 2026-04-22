"""Launch the AIIS Streamlit app (API starts automatically on port 8502)."""

import subprocess
import sys


def main():
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "app.py"],
        check=True,
    )


if __name__ == "__main__":
    main()
