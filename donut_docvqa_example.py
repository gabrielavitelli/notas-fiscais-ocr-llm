"""
Exemplo: Document Question Answering com Donut (Hugging Face).
Requer: pip install transformers datasets torch pillow
"""
import torch
from transformers import pipeline
from datasets import load_dataset

# Pipeline Donut para perguntas sobre documento (DocVQA)
pipe = pipeline(
    task="document-question-answering",
    model="naver-clova-ix/donut-base-finetuned-docvqa",
    device=0 if torch.cuda.is_available() else -1,  # -1 = CPU
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
)

# Dataset de exemplo (imagens de documentos)
dataset = load_dataset("hf-internal-testing/example-documents", split="test")
image = dataset[0]["image"]

# Pergunta sobre o documento
result = pipe(image=image, question="What time is the coffee break?")
print(result)
