import unittest

import beanstream.beanstream
import beanstream.billing

class BeanstreamTests(unittest.TestCase):

    def setUp(self):
        self.beanstream = beanstream.beanstream.Beanstream(hash_validation=True, require_billing_address=True)
        self.beanstream.configure(MERCHANT_ID, hashcode=HASHCODE, hash_algorithm='SHA1')

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

