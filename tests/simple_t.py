import ConfigParser
import unittest

import beanstream.beanstream
import beanstream.billing

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

        hash_validation = config.has_option('config', 'hash_validation')
        require_billing_address = config.has_option('config', 'require_billing_address')
        require_cvd = config.has_option('config', 'require_cvd')

        self.beanstream = beanstream.beanstream.Beanstream(
                hash_validation=hash_validation,
                require_billing_address=require_billing_address,
                require_cvd=require_cvd)
        self.beanstream.configure(
                merchant_id,
                hashcode=hashcode,
                hash_algorithm=hash_algorithm)

    def tearDown(self):
        pass

    def test_purchase(self):
        card = beanstream.billing.CreditCard(
            'John Doe',
            '4030000010001234',
            '05',
            '2015',
            '123')

        billing_address = beanstream.billing.Address(
            'John Doe',
            '555-555-5555',
            '123 Fake Street',
            '',
            'Fake City',
            'ON',
            'A1A1A1',
            'CA')

        self.beanstream.purchase(50, card, 'john.doe@example.com', billing_address)
        assert False

