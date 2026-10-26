import os
import signal
import subprocess
import sys
import time


def main():
    port = os.getenv("PORT", "8501")

    # Start Streamlit directly
    print(f"[*] Starting Streamlit application on port {port} ...")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "frontend/streamlit_app.py",
        "--server.port",
        str(port),
        "--server.address",
        "0.0.0.0",
        "--server.headless",
        "true",
    ]

    streamlit_process = subprocess.Popen(cmd)

    def shutdown(signum=None, frame=None):
        print("\n[*] Shutting down Streamlit...")
        try:
            streamlit_process.terminate()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    try:
        ret_code = streamlit_process.wait()
        sys.exit(ret_code)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
