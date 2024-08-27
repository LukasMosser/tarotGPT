import modal
from .tarot_flux import app as tarot_lora_app
from .modal_app import app as backend_app

app = modal.App("tarotGPT")
app.include(tarot_lora_app)