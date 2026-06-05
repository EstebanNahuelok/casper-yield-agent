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

    # Wallet
    vault_public_key: str
    vault_secret_key: str

    # Contratos
    vault_contract_hash: str
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
