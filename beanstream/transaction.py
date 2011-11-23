import decimal
import hashlib
import logging
import random
import string
import urllib
import urllib2
import urlparse

import errors

log = logging.getLogger('beanstream.transaction')


class Transaction(object):

    URLS = {
        'process_transaction'   : 'https://www.beanstream.com/scripts/process_transaction.asp',
        'recurring_billing'     : 'https://www.beanstream.com/scripts/recurring_billing.asp',
        'payment_profile'       : 'https://www.beanstream.com/scripts/payment_profile.asp',
    }

    TRN_TYPES = {
        'preauth': 'PA',
        'preauth_completion': 'PAC',
        'purchase': 'P',
        'return': 'R',
        'void': 'V',
        'void_purchase': 'VP',
        'void_return': 'VR',
    }


    def __init__(self, beanstream):
        self.beanstream = beanstream

        self.params = {}
        self.hashcode = None
        if self.beanstream.HASH_VALIDATION:
            self.hashcode = self.beanstream.hashcode

        elif self.beanstream.USERNAME_VALIDATION:
            self.params['username'] = self.beanstream.username
            self.params['password'] = self.beanstream.password

    def commit(self):
        # hashing is applicable only to requests sent to the process
        # transaction API.
        data = urllib.urlencode(self.params)
        if self.beanstream.HASH_VALIDATION and self.url == self.URLS['process_transaction']:
            if self.beanstream.hash_algorithm == 'MD5':
                hash = hashlib.md5()
            elif self.beanstream.hash_algorithm == 'SHA1':
                hash = hashlib.sha1()
            hash.update(data + self.beanstream.hashcode)
            hash_value = hash.hexdigest()
            data += '&hashValue=%s' % hash_value

        log.debug('Sending to %s: %s', self.url, data)

        res = urllib2.urlopen(self.url, data)

        if res.code != 200:
            log.error('response code not OK: %s', res.code)
            return False

        body = res.read()

        if body == 'Empty hash value':
            log.error('hash validation required')
            return False

        response = urlparse.parse_qs(body)
        log.debug('Beanstream response: %s', body)
        log.debug(response)

        return response

    def _generate_order_number(self):
        """ Generate a random 30-digit alphanumeric string.
        """
        self.order_number = ''.join((random.choice(string.ascii_lowercase + string.digits) for x in xrange(30)))

    def _process_billing_address(self, address):
        self.params.update(address.params('ord'))

    def _process_card(self, card):
        if self.beanstream.REQUIRE_CVD and not card.has_cvd():
            log.error('CVD required')
            raise errors.ValidationException('CVD required')

        self.params.update(card.params())

    def _process_amount(self, amount):
        decimal_amount = decimal.Decimal(amount)
        return str(decimal_amount.quantize(decimal.Decimal('1.00')))


class Purchase(Transaction):

    def __init__(self, beanstream_gateway, amount, card, email, billing_address):
        super(Purchase, self).__init__(beanstream_gateway)
        self.url = self.URLS['process_transaction']

        self.params['merchant_id'] = self.beanstream.merchant_id
        self.params['trnAmount'] = self._process_amount(amount)
        self.params['ordEmailAddress'] = email
        self.params['requestType'] = 'BACKEND'
        self.params['trnType'] = Transaction.TRN_TYPES['purchase']

        self._generate_order_number()
        self.params['trnOrderNumber'] = self.order_number

        self._process_card(card)

        if billing_address:
            self._process_billing_address(billing_address)

        elif self.beanstream.REQUIRE_BILLING_ADDRESS:
            log.error('billing address required')
            raise errors.ValidationException('billing address required')


class CreateRecurringBillingAccount(Purchase):
    """ Creating a recurring billing account is essentially doing a purchase
    transaction with some options specifying recurring billing.
    """

    def __init__(self, beanstream, amount, card, email, billing_address):
        super(CreateRecurringBillingAccount, self).__init__(beanstream, amount, card, email, billing_address)

        self.params['trnRecurring'] = '1'


class ModifyRecurringBillingAccount(Transaction):

    def __init__(self, beanstream):
        super(ModifyRecurringBillingAccount, self).__init__(beanstream)
        self.url = self.URLS['recurring_billing']

        self.params['merchantId'] = self.beanstream.merchant_id
        self.params['serviceVersion'] = '1.0'
        self.params['operationType'] = 'M'

