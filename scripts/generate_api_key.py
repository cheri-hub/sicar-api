"""
Script para gerar API Key segura.

Uso:
    python scripts/generate_api_key.py
"""

import secrets

def generate_api_key():
    """Gera uma API Key URL-safe de 32 bytes."""
    api_key = secrets.token_urlsafe(32)
    print("=" * 60)
    print("API KEY GERADA COM SUCESSO")
    print("=" * 60)
    print(f"\nAPI Key: {api_key}\n")
    print("INSTRUÇÕES:")
    print("1. Copie a chave acima")
    print("2. Adicione ao arquivo .env:")
    print(f"   API_KEY={api_key}")
    print("\n3. Reinicie a aplicação")
    print("\n4. Use a chave no header das requisições:")
    print("   X-API-Key: <sua-chave>")
    print("\nIMPORTANTE: Guarde esta chave em local seguro!")
    print("=" * 60)
    
    return api_key

if __name__ == "__main__":
    generate_api_key()
