import os
import signal
import subprocess
import sys
import time


def main():
    # Render assigns $PORT for the public-facing service.
    # Default to 8501 for local testing.
    public_port = os.getenv("PORT", "8501")
    internal_api_port = "8000"

    # Ensure Streamlit connects to the internal FastAPI backend if running in single-service mode
    current_api_url = os.getenv("API_URL", "")
    if (
        not current_api_url
        or "onrender.com" in current_api_url
        or "localhost" in current_api_url
        or "127.0.0.1" in current_api_url
    ):
        os.environ["API_URL"] = f"http://127.0.0.1:{internal_api_port}"

    print(f"[*] Starting FastAPI backend on http://127.0.0.1:{internal_api_port} ...")
    backend_process = subprocess.Popen([
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        internal_api_port,
    ])

    # Give FastAPI a moment to initialize
    time.sleep(2)

    print(f"[*] Starting Streamlit frontend on port {public_port} ...")
    streamlit_process = subprocess.Popen([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "frontend/streamlit_app.py",
        "--server.port",
        str(public_port),
        "--server.address",
        "0.0.0.0",
        "--server.headless",
        "true",
    ])

    def shutdown(signum=None, frame=None):
        print("\n[*] Shutting down services...")
        try:
            streamlit_process.terminate()
        except Exception:
            pass
        try:
            backend_process.terminate()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    try:
        ret_code = streamlit_process.wait()
        backend_process.terminate()
        sys.exit(ret_code)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
