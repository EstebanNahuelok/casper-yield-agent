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
    vault_contract_hash: str = "hash-0bcc5c99c90390e2f8c2259f097a860e93f14edd7c24047451986d44b99d3011"
    vault_package_hash: str = "d21679ac36362ccd8e3504d6a18c1386d5e1455ca7f948ee843be182ee8d2e38"
    scspr_contract_hash: str
    pool_package_hash: str = "79f783d4bdcb5d041bd7377a4f37b150e44bcf0628d3f44ae2e68901663544ad"

    # Red
    casper_network: str = "testnet"

    # Lógica del agente
    check_interval_seconds: int = 300
    min_apy_delta: float = 2.0
    max_slippage_pct: float = 1.5
    min_balance_cspr: float = 100.0
    swarm_vote_threshold: int = 2

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()
