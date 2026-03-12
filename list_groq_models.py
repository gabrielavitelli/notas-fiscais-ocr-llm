"""Lista modelos disponíveis na Groq. Uso: set GROQ_API_KEY=... e python list_groq_models.py"""
import requests
import os
import json

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print("Defina GROQ_API_KEY no ambiente.")
    exit(1)

url = "https://api.groq.com/openai/v1/models"
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
response = requests.get(url, headers=headers)
data = response.json()

if "data" in data:
    print("Modelos Groq (id):")
    for m in data["data"]:
        mid = m.get("id", m)
        print(f"  {mid}")
else:
    print(json.dumps(data, indent=2))
