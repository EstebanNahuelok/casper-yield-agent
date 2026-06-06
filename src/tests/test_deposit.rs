#[cfg(test)]
mod tests {
    use odra::casper_types::U512;
    use odra::host::{Deployer, HostRef};
    use odra_test::env;

    use crate::events::Deposit;
    use crate::vault::{YieldVault, YieldVaultInitArgs};

    fn setup() -> (odra::host::HostEnv, odra::prelude::Address, odra::prelude::Address) {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        env.set_caller(owner);
        (env, owner, agent)
    }

    #[test]
    fn deposit_increases_user_balance() {
        let (env, _owner, agent) = setup();
        let vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        let user = env.get_account(2);
        env.set_caller(user);

        let amount = U512::from(1_000_000_000u64); // 1 CSPR en motes
        vault.with_tokens(amount).deposit();

        assert_eq!(vault.get_balance(user), amount);
        assert!(env.emitted_event(
            &vault,
            Deposit { user, amount, new_balance: amount, timestamp: 0 },
        ));
    }

    #[test]
    fn deposit_increases_total_locked() {
        let (env, _owner, agent) = setup();
        let vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        let user = env.get_account(2);
        env.set_caller(user);
        let amount = U512::from(2_000_000_000u64);

        vault.with_tokens(amount).deposit();

        assert_eq!(vault.get_total_locked(), amount);
    }

    #[test]
    fn multiple_deposits_accumulate() {
        let (env, _owner, agent) = setup();
        let vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        let user = env.get_account(2);
        env.set_caller(user);

        let first = U512::from(1_000_000_000u64);
        let second = U512::from(500_000_000u64);

        vault.with_tokens(first).deposit();
        vault.with_tokens(second).deposit();

        assert_eq!(vault.get_balance(user), first + second);
        assert_eq!(vault.get_total_locked(), first + second);
    }

    #[test]
    #[should_panic]
    fn deposit_zero_reverts() {
        let (env, _owner, agent) = setup();
        let vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        let user = env.get_account(2);
        env.set_caller(user);

        vault.with_tokens(U512::zero()).deposit();
    }

    #[test]
    #[should_panic]
    fn deposit_while_paused_reverts() {
        let (env, owner, agent) = setup();
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(owner);
        vault.pause();

        let user = env.get_account(2);
        env.set_caller(user);
        vault.with_tokens(U512::from(1_000_000_000u64)).deposit();
    }

    #[test]
    fn two_users_balances_are_independent() {
        let (env, _owner, agent) = setup();
        let vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        let user_a = env.get_account(2);
        let user_b = env.get_account(3);

        let amount_a = U512::from(1_000_000_000u64);
        let amount_b = U512::from(3_000_000_000u64);

        env.set_caller(user_a);
        vault.with_tokens(amount_a).deposit();

        env.set_caller(user_b);
        vault.with_tokens(amount_b).deposit();

        assert_eq!(vault.get_balance(user_a), amount_a);
        assert_eq!(vault.get_balance(user_b), amount_b);
        assert_eq!(vault.get_total_locked(), amount_a + amount_b);
    }
}
