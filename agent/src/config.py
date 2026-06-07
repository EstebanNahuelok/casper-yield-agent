from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # LLM
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    # MCP
    casper_mcp_url: str = "http://localhost:3001/mcp"
    cspr_cloud_api_key: str
    csprtrade_mcp_url: str = "https://mcp.cspr.trade/mcp"

    # Wallet (owner y agente comparten la misma keypair)
    vault_public_key: str
    vault_owner_public_key: str = "01c3acc1af3faa221073e5928bf74d58ad9ad9e58be2bdc39218a25e5ddff72309"
    vault_owner_secret_key: str

    # Contratos
    vault_contract_hash: str = "hash-6c5fe09ddc4ca76adfa2790bf7a58767eba32020a50e606a14a8ef803a89a06a"
    scspr_contract_hash: str

    # Red
    casper_network: str = "testnet"

    # Lógica del agente
    check_interval_seconds: int = 300
    min_apy_delta: float = 2.0
    max_slippage_pct: float = 1.5
    min_balance_cspr: float = 100.0

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
