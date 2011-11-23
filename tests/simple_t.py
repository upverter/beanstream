import ConfigParser
from datetime import date
import unittest

from beanstream import gateway
from beanstream import billing


class BeanstreamTests(unittest.TestCase):

    def setUp(self):
        config = ConfigParser.SafeConfigParser()
        config.read('beanstream.cfg')
        merchant_id = config.get('beanstream', 'merchant_id')

        hashcode = None
        if config.has_option('beanstream', 'hashcode'):
            hashcode = config.get('beanstream', 'hashcode')

        hash_algorithm = None
        if config.has_option('beanstream', 'hash_algorithm'):
            hash_algorithm = config.get('beanstream', 'hash_algorithm')

        payment_profile_passcode = None
        if config.has_option('beanstream', 'payment_profile_passcode'):
            payment_profile_passcode = config.get('beanstream', 'payment_profile_passcode')

        hash_validation = config.has_option('config', 'hash_validation')
        require_billing_address = config.has_option('config', 'require_billing_address')
        require_cvd = config.has_option('config', 'require_cvd')

        self.beanstream = gateway.Beanstream(
                hash_validation=hash_validation,
                require_billing_address=require_billing_address,
                require_cvd=require_cvd)
        self.beanstream.configure(
                merchant_id,
                hashcode=hashcode,
                hash_algorithm=hash_algorithm,
                payment_profile_passcode=payment_profile_passcode)

        self.approved_cards = {'visa': {'number': '4030000010001234', 'cvd': '123'},
                               '100_visa': {'number': '4504481742333', 'cvd': '123'},
                               'vbv_visa': {'nubmer': '4123450131003312', 'cvd': '123', 'vbv': '12345'},
                               'mc1': {'number': '5100000010001004', 'cvd': '123'},
                               'mc2': {'number': '5194930004875020', 'cvd': '123'},
                               'mc3': {'number': '5123450000002889', 'cvd': '123'},
                               '3d_mc': {'number': '5123450000000000', 'cvd': '123', 'passcode': '12345'},
                               'amex': {'number': '371100001000131', 'cvd': '1234'},
                               'discover': {'number': '6011500080009080', 'cvd': '123'},
                              }
        self.declined_cards = {'visa': {'number': '4003050500040005', 'cvd': '123'},
                               'mc': {'number': '5100000020002000', 'cvd': '123'},
                               'amex': {'number': '342400001000180', 'cvd': '1234'},
                               'discover': {'number': '6011000900901111', 'cvd': '123'},
                              }

        self.billing_address = billing.Address(
            'John Doe',
            'john.doe@example.com',
            '555-555-5555',
            '123 Fake Street',
            '',
            'Fake City',
            'ON',
            'A1A1A1',
            'CA')

    def tearDown(self):
        pass

    def test_successful_cc_purchase(self):
        today = date.today()
        visa = self.approved_cards['visa']
        card = billing.CreditCard(
            'John Doe',
            visa['number'],
            str(today.month), str(today.year + 3),
            visa['cvd'])

        txn = self.beanstream.purchase(50, card, self.billing_address)
        resp = txn.commit()
        assert resp.approved()
        assert resp.cvd_status() == 'CVD Match'

    def test_failed_cvd(self):
        today = date.today()
        visa = self.approved_cards['visa']
        card = billing.CreditCard(
            'John Doe',
            visa['number'],
            str(today.month), str(today.year + 3),
            '000')

        txn = self.beanstream.purchase(50, card, self.billing_address)
        resp = txn.commit()
        assert not resp.approved()
        assert resp.cvd_status() == 'CVD Mismatch'


    def test_over_limit_cc_purchase(self):
        today = date.today()
        visa_limit = self.approved_cards['100_visa']
        card = billing.CreditCard(
            'John Doe',
            visa_limit['number'],
            str(today.month), str(today.year + 3),
            visa_limit['cvd'])

        txn = self.beanstream.purchase(250, card, self.billing_address)
        resp = txn.commit()
        assert not resp.approved()
        assert resp.cvd_status() == 'CVD Match'

    def test_create_recurring_billing(self):
        today = date.today()
        visa = self.approved_cards['visa']
        card = billing.CreditCard(
            'John Doe',
            visa['number'],
            str(today.month), str(today.year + 3),
            visa['cvd'])

        txn = self.beanstream.create_recurring_billing_account(50, card, 'w', 2, billing_address=self.billing_address)
        resp = txn.commit()
        assert resp.approved()
        assert resp.cvd_status() == 'CVD Match'
        assert resp.account_id() is not None

    def test_payment_profiles(self):
        today = date.today()
        visa = self.approved_cards['visa']
        card = billing.CreditCard(
            'John Doe',
            visa['number'],
            str(today.month), str(today.year + 3),
            visa['cvd'])

        txn = self.beanstream.create_payment_profile(card, billing_address=self.billing_address)
        create_resp = txn.commit()
        assert create_resp.approved()

        txn = self.beanstream.purchase_with_payment_profile(50, create_resp.customer_code())
        purchase_resp = txn.commit()
        assert purchase_resp.approved()

        txn = self.beanstream.modify_payment_profile(create_resp.customer_code())
        txn.set_status('D')
        modify_resp = txn.commit()
        assert modify_resp.approved()

        txn = self.beanstream.purchase_with_payment_profile(50, create_resp.customer_code())
        purchase_resp2 = txn.commit()
        assert not purchase_resp2.approved()

