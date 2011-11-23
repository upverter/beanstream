from beanstream import errors
from beanstream import transaction

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

    def configure(self, merchant_id, **params):
        """ Configure the gateway.

        Keyword arguments:
            hashcode: required if hash validation is enabled.
            hash_algorithm: required if hash validation is enabled; one of MD5 or SHA1.
            username: required if username validation is enabled.
            password: required if username validation is enabled.
        """
        self.merchant_id = merchant_id
        self.hashcode = params.get('hashcode', None)
        self.hash_algorithm = params.get('hash_algorithm', None)
        self.username = params.get('username', None)
        self.password = params.get('password', None)

        if self.HASH_VALIDATION and (not self.hashcode or not self.hash_algorithm):
            raise errors.ConfigurationException('hashcode and algorithm must be specified')

        if self.USERNAME_VALIDATION and (not self.username or not self.password):
            raise errors.ConfigurationException('username and password must be specified')

    def purchase(self, amount, card, email, billing_address=None):
        """ Performs a one-off credit card purchase.
        """
        txn = transaction.Purchase(self, amount, card, email, billing_address)
        return txn.commit()

    def void_purchase(self):
        """ Voids a purchase.
        """
        raise NotImplementedException

    def return_purchase(self):
        pass

    def void_return(self):
        """ Voids a return.
        """
        pass

    def preauth(self):
        """ Performs a pre-authorizataion.
        """
        pass

    def cancel_preauth(self):
        pass

    def preauth_completion(self):
        pass


    def create_profile(self):
        pass

    def modify_profile(self):
        pass

    def purchase_with_profile(self):
        """ Performs a one-off credit card purchase against a payment profile.
        """
        pass

    def create_recurring_billing_account(self, amount, card, email, billing_address=None):
        txn = transaction.CreateRecurringBillingAccount(self, amount, card, email, billing_address)
        txn.commit()

    def modify_recurring_billing_account(self):
        pass

