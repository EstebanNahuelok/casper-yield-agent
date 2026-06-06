#[cfg(test)]
mod tests {
    use odra::casper_types::U512;
    use odra::host::Deployer;
    use odra_test::env;

    use crate::events::{ActionLogged, SwapExecuted};
    use crate::vault::{YieldVault, YieldVaultInitArgs};

    #[test]
    fn agent_can_log_action() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(agent);
        vault.log_action("REBALANCE".into(), r#"{"ratio":0.5}"#.into());

        assert_eq!(vault.get_action_count(), 1);
        assert!(env.emitted_event(
            &vault,
            ActionLogged { id: 0, action_type: "REBALANCE".to_string(), agent, timestamp: 0 },
        ));
    }

    #[test]
    fn get_last_action_returns_latest() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(agent);
        vault.log_action("HARVEST".into(), "{}".into());
        vault.log_action("COMPOUND".into(), r#"{"amount":100}"#.into());

        let last = vault.get_last_action().expect("should have a last action");
        assert_eq!(last.action_type, "COMPOUND");
        assert_eq!(last.id, 1);
    }

    #[test]
    fn get_last_action_on_empty_returns_none() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        assert!(vault.get_last_action().is_none());
    }

    #[test]
    fn action_count_increments_correctly() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        assert_eq!(vault.get_action_count(), 0);

        env.set_caller(agent);
        for i in 0..5u64 {
            vault.log_action("ACTION".into(), format!("{{\"i\":{}}}", i));
        }

        assert_eq!(vault.get_action_count(), 5);
    }

    #[test]
    fn get_action_by_id_returns_correct_entry() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(agent);
        vault.log_action("FIRST".into(), "{}".into());
        vault.log_action("SECOND".into(), "{}".into());

        let entry = vault.get_action(0).expect("should exist");
        assert_eq!(entry.action_type, "FIRST");
        assert_eq!(entry.id, 0);
    }

    #[test]
    fn get_action_out_of_bounds_returns_none() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        assert!(vault.get_action(999).is_none());
    }

    #[test]
    #[should_panic]
    fn non_agent_cannot_log_action() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let attacker = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(attacker);
        vault.log_action("ATTACK".into(), "{}".into());
    }

    #[test]
    #[should_panic]
    fn owner_cannot_log_action_directly() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        // Owner ≠ agent — no debería poder loggear
        vault.log_action("OWNER_LOG".into(), "{}".into());
    }

    #[test]
    fn agent_can_execute_swap() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(agent);
        vault.execute_swap(
            "CSPR".into(),
            "USDC".into(),
            U512::from(1_000_000_000u64),
            U512::from(980_000_000u64),
        );

        assert_eq!(vault.get_swap_count(), 1);
        let swap = vault.get_swap(0).expect("swap 0 should exist");
        assert_eq!(swap.token_in, "CSPR");
        assert_eq!(swap.token_out, "USDC");
        assert!(env.emitted_event(
            &vault,
            SwapExecuted {
                id: 0,
                token_in: "CSPR".to_string(),
                token_out: "USDC".to_string(),
                amount_in: U512::from(1_000_000_000u64),
                amount_out: U512::from(980_000_000u64),
                timestamp: 0,
            },
        ));
    }

    #[test]
    #[should_panic]
    fn execute_swap_with_zero_amount_reverts() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(agent);
        vault.execute_swap(
            "CSPR".into(),
            "USDC".into(),
            U512::zero(),
            U512::from(1_000_000_000u64),
        );
    }

    #[test]
    #[should_panic]
    fn execute_swap_same_token_reverts() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(agent);
        vault.execute_swap(
            "CSPR".into(),
            "CSPR".into(),
            U512::from(1_000_000_000u64),
            U512::from(1_000_000_000u64),
        );
    }

    #[test]
    #[should_panic]
    fn execute_swap_empty_token_in_reverts() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(agent);
        vault.execute_swap(
            "".into(),
            "USDC".into(),
            U512::from(1_000_000_000u64),
            U512::from(980_000_000u64),
        );
    }

    #[test]
    #[should_panic]
    fn log_action_empty_type_reverts() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(agent);
        vault.log_action("".into(), "{}".into());
    }
}
