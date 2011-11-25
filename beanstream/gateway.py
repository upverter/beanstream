from beanstream import errors, payment_profiles, process_transaction, recurring_billing, reports

class Beanstream(object):

    HASH_VALIDATION = False
    USERNAME_VALIDATION = False
    REQUIRE_CVD = False
    REQUIRE_BILLING_ADDRESS = False

    def __init__(self, **options):
        """ Initialize the gateway.

        Keyword arguments:
            hash_validation: True to enable; default disabled. Note that
                hash_validation and username_validation may not be enabled
                simultaneously.
            username_validation: True to enable; default disabled. Note that
                username_validation and hash_validation may not be enabled
                simultaneously.
            require_cvd: True to enable; default disabled.
            require_billing_address: True to enable; default disabled.
        """

        self.HASH_VALIDATION = options.get('hash_validation', False)
        self.USERNAME_VALIDATION = options.get('username_validation', False)
        self.REQUIRE_CVD = options.get('require_cvd', False)
        self.REQUIRE_BILLING_ADDRESS = options.get('require_billing_address', False)

        if self.HASH_VALIDATION and self.USERNAME_VALIDATION:
            raise errors.ConfigurationException('Only one validation method may be specified')

        self.merchant_id = None
        self.username = None
        self.password = None
        self.hashcode = None
        self.payment_profile_passcode = None

    def configure(self, merchant_id, login_company, login_user, login_password, **params):
        """ Configure the gateway.

        Keyword arguments:
            hashcode: required if hash validation is enabled.
            hash_algorithm: required if hash validation is enabled; one of MD5 or SHA1.
            username: required if username validation is enabled.
            password: required if username validation is enabled.
        """
        self.merchant_id = merchant_id
        self.login_company = login_company
        self.login_user = login_user
        self.login_password = login_password
        self.hashcode = params.get('hashcode', None)
        self.hash_algorithm = params.get('hash_algorithm', None)
        self.username = params.get('username', None)
        self.password = params.get('password', None)
        self.payment_profile_passcode = params.get('payment_profile_passcode', None)
        self.recurring_billing_passcode = params.get('recurring_billing_passcode', None)

        if self.HASH_VALIDATION and (not self.hashcode or not self.hash_algorithm):
            raise errors.ConfigurationException('hashcode and algorithm must be specified')

        if self.USERNAME_VALIDATION and (not self.username or not self.password):
            raise errors.ConfigurationException('username and password must be specified')

        if self.HASH_VALIDATION and self.hash_algorithm not in ('MD5', 'SHA1'):
            raise errors.ConfigurationException('hash algorithm must be one of MD5 or SHA1')

    def purchase(self, amount, card, billing_address=None):
        """ Returns a Purchase object with the specified options.
        """
        txn = process_transaction.Purchase(self, amount)
        txn.set_card(card)
        if billing_address:
            txn.set_billing_address(billing_address)

        return txn

    def void_purchase(self, transaction_id, amount):
        """ Returns an Adjustment object configured for voiding the specified
        transaction for the specified amount.
        """
        txn = process_transaction.Adjustment(self, process_transaction.Adjustment.VOID, transaction_id, amount)
        return txn

    def return_purchase(self, transaction_id, amount):
        """ Returns an Adjustment object configured for returning the specified
        transaction for the specified amount.
        """
        txn = process_transaction.Adjustment(self, process_transaction.Adjustment.RETURN, transaction_id, amount)
        return txn

    def void_return(self, transaction_id, amount):
        """ Returns an Adjustment object configured for voiding the return of
        the specified transaction for the specified amount.
        """
        txn = process_transaction.Adjustment(self, process_transaction.Adjustment.VOID_RETURN, transaction_id, amount)
        return txn

    def preauth(self, amount, card, billing_address=None):
        """ Returns a PreAuthorization object with the specified options.
        """
        txn = process_transaction.PreAuthorization(self, amount)
        txn.set_card(card)
        if billing_address:
            txn.set_billing_address(billing_address)

        return txn

    def preauth_completion(self, transaction_id, amount):
        """ Returns an Adjustment object configured for completing the
        preauthorized transaction for the specified amount.
        """
        txn = process_transaction.Adjustment(self, process_transaction.Adjustment.PREAUTH_COMPLETION, transaction_id, amount)
        return txn

    def cancel_preauth(self, transaction_id):
        """ Returns an Adjustment object configured for cancelling the
        preauthorized transaction.
        """
        txn = process_transaction.Adjustment(self, process_transaction.Adjustment.PREAUTH_COMPLETION, transaction_id, 0)
        return txn

    def create_payment_profile(self, card, billing_address=None):
        """ Returns a CreatePaymentProfile object with the specified options.
        """
        txn = payment_profiles.CreatePaymentProfile(self, card)
        if billing_address:
            txn.set_billing_address(billing_address)

        return txn

    def modify_payment_profile(self, customer_code):
        """ Returns a ModifyPaymentProfile object with the specified options.
        """
        txn = payment_profiles.ModifyPaymentProfile(self, customer_code)
        return txn

    def get_payment_profile(self, customer_code):
        """ Returns a GetPaymentProfile object with the specified options.
        """
        txn = payment_profiles.GetPaymentProfile(self, customer_code)
        return txn

    def purchase_with_payment_profile(self, amount, customer_code):
        """ Returns a Purchase object with the specified options.
        """
        txn = process_transaction.Purchase(self, amount)
        txn.set_customer_code(customer_code)
        return txn

    def preauth_with_payment_profile(self, amount, customer_code):
        """ Returns a PreAuthorization object with the specified options.
        """
        txn = process_transaction.PreAuthorization(self, amount)
        txn.set_card(card)
        if billing_address:
            txn.set_billing_address(billing_address)

        return txn

    def create_recurring_billing_account_from_payment_profile(self, amount,
            customer_code, frequency_period, frequency_increment):
        """ Returns a CreateRecurringBillingAccount object with the specified
        options.
        """
        txn = recurring_billing.CreateRecurringBillingAccount(self, amount,
                frequency_period, frequency_increment)
        txn.set_customer_code(customer_code)
        return txn

    def create_recurring_billing_account(self, amount, card, frequency_period,
            frequency_increment, billing_address=None):
        """ Returns a CreateRecurringBillingAccount object with the specified
        options.
        """
        txn = recurring_billing.CreateRecurringBillingAccount(self, amount,
                frequency_period, frequency_increment)
        txn.set_card(card)
        if billing_address:
            txn.set_billing_address(billing_address)

        return txn

    def modify_recurring_billing_account(self, account_id):
        """ Returns a ModifyRecurringBillingAccount object with the specified
        options.
        """
        txn = recurring_billing.ModifyRecurringBillingAccount(self, account_id)
        return txn


    def get_transaction_report(self):
        """ Returns a TransactionReport object.
        """
        txn = reports.TransactionReport(self)
        return txn

    def get_transaction_set_report(self, transaction_ids):
        """ Returns a TransactionSetReport object for the specified set of
        transaction IDs.
        """
        txn = reports.TransactionSetReport(self, transaction_ids)

        return txn

    def get_credit_card_lookup_report(self, card_number=None, txn_id=None):
        """ Returns a CreditCardLookupReport object with the specified options.
        """
        txn = reports.CreditCardLookupReport(self)
        if card_number:
            txn.set_credit_card_number(card_number)
        if txn_id:
            txn.set_transaction_id(txn_id)

        return txn

