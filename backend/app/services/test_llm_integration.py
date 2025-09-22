# test_llm_integration.py
from llm_integration import AnonymizationPipeline

def main():
    pipeline = AnonymizationPipeline()

    # Ejemplos de textos con PII
    examples = [
        {
            "text": "Mi nombre es Juan Pérez y mi email es juanperez@gmail.com",
        },
        {
            "text": "Llámame al +34 612345678 o envíame un correo a contacto@empresa.es",
        },
        {
            "text": "Mi DNI es 12345678Z y trabajo en Acme Corporation en Madrid",
        },
    ]

    for i, ex in enumerate(examples, 1):
        text = ex["text"]
        print(f"\n--- Ejemplo {i} ---")
        print("Texto original:", text)
        result = pipeline.run_pipeline(text)
        print("Resultado final:", result)

if __name__ == "__main__":
    main()

