import modal
from modal_tarot_flux import app as tarot_lora_app
from modal_deploy_streamlit import app as frontend_app

app = modal.App("tarotGPT")
app.include(tarot_lora_app)
app.include(frontend_app)