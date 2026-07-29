from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

# Listar todos los modelos soportados
for m in client.models.list():
    print(m.name)