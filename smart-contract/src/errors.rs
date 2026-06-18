// OdraError debe estar en scope porque el macro #[odra::odra_error]
// genera `impl From<VaultError> for OdraError` sin path completo.
use odra::prelude::OdraError;

/// Códigos de error del YieldVault.
/// Rango 30_000–30_099 reservado para este contrato.
/// Rango válido de usuario: 0..64_535 (ExecutionError::MaxUserError).
#[odra::odra_error]
pub enum VaultError {
    InsufficientBalance = 30_000,
    Unauthorized        = 30_001,
    ContractPaused      = 30_002,
    InvalidAmount       = 30_003,
    ActionLimitReached  = 30_004,
    ArithmeticOverflow  = 30_005,
    InvalidInputLength  = 30_006,
    InvalidSwap         = 30_007,
    PoolNotSet          = 30_008,
    InsufficientLiquidity = 30_009,
    SlippageExceeded    = 30_010,
}
