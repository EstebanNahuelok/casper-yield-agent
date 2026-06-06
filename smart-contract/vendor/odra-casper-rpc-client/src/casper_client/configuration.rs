use crate::casper_client::{
    ENV_ACCOUNT_PREFIX, ENV_CHAIN_NAME, ENV_CSPR_CLOUD_AUTH_TOKEN, ENV_EVENTS_ADDRESS,
    ENV_LIVENET_ENV_FILE, ENV_NODE_ADDRESS, ENV_SECRET_KEY, ENV_TTL
};
use crate::log;
use crate::utils::{get_env_variable, get_optional_env_variable};
use casper_client::Verbosity;
use casper_types::TimeDiff;
use odra_core::casper_types::SecretKey;
use std::path::PathBuf;

pub const DEFAULT_TTL: u32 = 5 * 60; // Seconds.
pub const DEFAULT_GAS_TOLERANCE: u8 = 5;

#[derive(Debug)]
pub struct CasperClientConfiguration {
    pub node_address: String,
    pub events_url: String,
    pub chain_name: String,
    pub secret_keys: Vec<SecretKey>,
    pub secret_key_paths: Vec<String>,
    pub cspr_cloud_auth_token: Option<String>,
    pub ttl: u32
}

impl CasperClientConfiguration {
    /// Force-loads a dotenv file, overriding any pre-existing shell env vars.
    /// dotenv's default `load()` skips keys already present in the environment,
    /// which causes stale shell exports to shadow the .env file values.
    fn force_load_dotenv_file(path: &std::path::Path) {
        if let Ok(content) = std::fs::read_to_string(path) {
            for line in content.lines() {
                let line = line.trim();
                if line.is_empty() || line.starts_with('#') {
                    continue;
                }
                if let Some(eq) = line.find('=') {
                    let key = line[..eq].trim();
                    let val = line[eq + 1..].trim().trim_matches('"').trim_matches('\'');
                    std::env::set_var(key, val);
                }
            }
        }
    }

    pub fn from_env() -> Self {
        // Check for additional .env file
        let additional_env_file = std::env::var(ENV_LIVENET_ENV_FILE);

        if let Ok(additional_env_file) = additional_env_file {
            let filename = PathBuf::from(&additional_env_file).with_extension("env");
            Self::force_load_dotenv_file(&filename);
        }

        // Force-load .env, overriding stale shell exports.
        // dotenv::dotenv() silently skips keys that already exist in the env,
        // which means a previously `source`d .env with old values wins over
        // the current .env file.  We walk up the directory tree to find .env
        // the same way dotenv would, then apply it with unconditional set_var.
        {
            let mut dir = std::env::current_dir().ok();
            let mut found = false;
            while let Some(d) = dir {
                let candidate = d.join(".env");
                if candidate.exists() {
                    Self::force_load_dotenv_file(&candidate);
                    found = true;
                    break;
                }
                dir = d.parent().map(|p| p.to_path_buf());
            }
            if !found {
                // Fallback: let dotenv try its normal load so other env mechanisms still work
                dotenv::dotenv().ok();
            }
        }

        // Initialize logging from environment variable
        log::init_log_level();

        let node_address = get_env_variable(ENV_NODE_ADDRESS);
        let chain_name = get_env_variable(ENV_CHAIN_NAME);
        let events_url = get_env_variable(ENV_EVENTS_ADDRESS);
        let ttl = get_optional_env_variable(ENV_TTL)
            .and_then(|ttl| ttl.parse::<u32>().ok())
            .unwrap_or(DEFAULT_TTL);

        let (secret_keys, secret_key_paths) = Self::secret_keys_from_env();
        CasperClientConfiguration {
            node_address,
            chain_name,
            secret_keys,
            secret_key_paths,
            cspr_cloud_auth_token: get_optional_env_variable(ENV_CSPR_CLOUD_AUTH_TOKEN),
            events_url,
            ttl
        }
    }

    /// Loads secret keys from ENV_SECRET_KEY file and ENV_ACCOUNT_PREFIX files.
    /// e.g. ENV_SECRET_KEY=secret_key.pem, ENV_ACCOUNT_PREFIX=account_1_key.pem
    /// This will load secret_key.pem as account 0 and account_1_key.pem as account 1.
    fn secret_keys_from_env() -> (Vec<SecretKey>, Vec<String>) {
        let mut secret_keys = vec![];
        let mut secret_key_paths = vec![];
        let file_name = get_env_variable(ENV_SECRET_KEY);
        secret_keys.push(SecretKey::from_file(file_name.clone()).unwrap_or_else(|_| {
            panic!(
                "Couldn't load secret key from file {:?}",
                get_env_variable(ENV_SECRET_KEY)
            )
        }));
        secret_key_paths.push(file_name);

        let mut i = 1;
        while let Ok(key_filename) = std::env::var(format!("{}{}", ENV_ACCOUNT_PREFIX, i)) {
            secret_keys.push(SecretKey::from_file(&key_filename).unwrap_or_else(|_| {
                panic!("Couldn't load secret key from file {:?}", key_filename)
            }));
            secret_key_paths.push(key_filename);
            i += 1;
        }
        (secret_keys, secret_key_paths)
    }

    pub fn verbosity(&self) -> u64 {
        Verbosity::Low as u64
    }

    pub fn verbosity_typed(&self) -> Verbosity {
        Verbosity::Low
    }

    pub fn ttl(&self) -> TimeDiff {
        TimeDiff::from_seconds(self.ttl)
    }

    pub fn chain_name(&self) -> &str {
        &self.chain_name
    }

    /// Node rpc address.
    pub fn node_address_rpc(&self) -> String {
        format!("{}/rpc", self.node_address())
    }

    /// Node address.
    pub fn node_address(&self) -> &str {
        &self.node_address
    }

    /// Gas price tolerance
    pub fn gas_price_tolerance(&self) -> u8 {
        DEFAULT_GAS_TOLERANCE
    }

    pub fn transaction_url(&self, transaction_id: &str) -> Option<String> {
        match self.chain_name.as_str() {
            "casper-test" => Some(format!(
                "https://testnet.cspr.live/transaction/{}",
                transaction_id
            )),
            "casper" => Some(format!("https://cspr.live/transaction/{}", transaction_id)),
            _ => None
        }
    }
}
