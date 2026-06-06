#[cfg(test)]
mod tests {
    use odra::casper_types::U512;
    use odra::host::{Deployer, HostRef};
    use odra_test::env;

    use crate::events::Withdrawal;
    use crate::vault::{YieldVault, YieldVaultInitArgs};

    #[test]
    fn withdraw_decreases_balance() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let user = env.get_account(2);
        let deposit = U512::from(2_000_000_000u64);
        let withdraw_amount = U512::from(500_000_000u64);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });
        env.set_caller(user);
        vault.with_tokens(deposit).deposit();
        vault.withdraw(withdraw_amount);

        assert_eq!(vault.get_balance(user), deposit - withdraw_amount);
        assert!(env.emitted_event(
            &vault,
            Withdrawal { user, amount: withdraw_amount, remaining_balance: deposit - withdraw_amount, timestamp: 0 },
        ));
    }

    #[test]
    fn withdraw_decreases_total_locked() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let user = env.get_account(2);
        let deposit = U512::from(2_000_000_000u64);
        let withdraw_amount = U512::from(500_000_000u64);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });
        env.set_caller(user);
        vault.with_tokens(deposit).deposit();
        vault.withdraw(withdraw_amount);

        assert_eq!(vault.get_total_locked(), deposit - withdraw_amount);
    }

    #[test]
    fn full_withdrawal_zeroes_balance() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let user = env.get_account(2);
        let deposit = U512::from(1_000_000_000u64);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });
        env.set_caller(user);
        vault.with_tokens(deposit).deposit();
        vault.withdraw(deposit);

        assert_eq!(vault.get_balance(user), U512::zero());
        assert_eq!(vault.get_total_locked(), U512::zero());
    }

    #[test]
    #[should_panic]
    fn withdraw_more_than_balance_reverts() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let user = env.get_account(2);
        let deposit = U512::from(1_000_000_000u64);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });
        env.set_caller(user);
        vault.with_tokens(deposit).deposit();
        vault.withdraw(deposit + U512::from(1u64));
    }

    #[test]
    #[should_panic]
    fn withdraw_zero_reverts() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let user = env.get_account(2);
        let deposit = U512::from(1_000_000_000u64);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });
        env.set_caller(user);
        vault.with_tokens(deposit).deposit();
        vault.withdraw(U512::zero());
    }

    #[test]
    #[should_panic]
    fn withdraw_from_empty_account_reverts() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let non_depositor = env.get_account(3);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });
        env.set_caller(non_depositor);
        vault.withdraw(U512::from(1_000_000_000u64));
    }

    #[test]
    #[should_panic]
    fn withdraw_while_paused_reverts() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let user = env.get_account(2);
        let deposit = U512::from(1_000_000_000u64);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });
        env.set_caller(user);
        vault.with_tokens(deposit).deposit();
        env.set_caller(owner);
        vault.pause();
        env.set_caller(user);
        vault.withdraw(deposit);
    }

    #[test]
    fn other_user_balance_stays_zero_after_depositor_deposits() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let depositor = env.get_account(2);
        let other = env.get_account(3);
        let deposit = U512::from(2_000_000_000u64);

        env.set_caller(owner);
        let vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });
        env.set_caller(depositor);
        vault.with_tokens(deposit).deposit();

        assert_eq!(vault.get_balance(other), U512::zero());
        assert_eq!(vault.get_total_locked(), deposit);
    }

    #[test]
    #[should_panic]
    fn other_user_withdraw_attempt_reverts() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let depositor = env.get_account(2);
        let other = env.get_account(3);
        let deposit = U512::from(2_000_000_000u64);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });
        env.set_caller(depositor);
        vault.with_tokens(deposit).deposit();

        // Other nunca depositó — intentar retirar 1 mote debe revertir
        env.set_caller(other);
        vault.withdraw(U512::from(1u64));
    }
}
