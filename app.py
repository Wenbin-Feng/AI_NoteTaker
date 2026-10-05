"""Flask entrypoint detected by Vercel."""
from src.main import create_app

app = create_app()
