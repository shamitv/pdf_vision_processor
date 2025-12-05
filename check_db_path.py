
from pdf_vision_processor.settings import get_settings
from dotenv import load_dotenv

load_dotenv()
settings = get_settings()
print(f"Active Database URL: {settings.database_url}")
