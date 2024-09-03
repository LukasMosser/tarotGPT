import shlex
import subprocess
from pathlib import Path

import modal


image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "streamlit", "openai", "modal", "img2pdf"
)

app = modal.App(name="tarot-gpt-streamlit-frontend", image=image)

streamlit_script_local_path = Path(__file__).parent / "tarotGPT.py"
streamlit_script_remote_path = Path("/root/tarotGPT.py")

if not streamlit_script_local_path.exists():
    raise RuntimeError(
        "app.py not found! Place the script with your streamlit app in the same directory."
    )

streamlit_script_mount = modal.Mount.from_local_file(
    streamlit_script_local_path,
    streamlit_script_remote_path,
)

streamlit_pages_folder_mount = modal.Mount.from_local_dir(
    local_path=Path(__file__).parent / "pages", 
    remote_path="/root/pages"
)

@app.function(
    image=image,
    allow_concurrent_inputs=100,
    concurrency_limit=1,
    mounts=[streamlit_script_mount, streamlit_pages_folder_mount],
    secrets=[modal.Secret.from_name("tarot-gpt-openai-key")],
    timeout=60*25,
    container_idle_timeout=60*20,
)
@modal.web_server(8501)
def run():
    target = shlex.quote(str(streamlit_script_remote_path))
    cmd = f"streamlit run {target} --server.port 8501 --server.headless true"
    subprocess.Popen(cmd, shell=True)