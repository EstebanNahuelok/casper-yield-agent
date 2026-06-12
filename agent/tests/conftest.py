import os

# Variables mínimas para que Settings() no falle en tests (sin .env real)
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("CSPR_CLOUD_API_KEY", "test-cspr-key")
os.environ.setdefault("VAULT_PUBLIC_KEY", "01aabbcc")
os.environ.setdefault("VAULT_OWNER_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SCSPR_CONTRACT_HASH", "test-scspr-hash")
