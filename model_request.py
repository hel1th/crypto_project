from transformers import AutoTokenizer, MistralForCausalLM
import torch

model_path = r"C:\Проекты\pythonProject\mistral_model"

# Загрузка модели и токенизатора
tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, legacy=False)
model = MistralForCausalLM.from_pretrained(model_path, local_files_only=True)
model = model.to("cpu") # можно указать cuda

question, text = "What is an Earth?", "Earth is out planet"
prompt = f"Question: {question}\nContext: {text}\nAnswer:"
inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to("cpu")

# Генерация ответа
with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=50)

answer = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(answer)
