import decimal
import hashlib
import logging
import random
import string
import urllib
import urllib2
import urlparse

from beanstream import errors
from beanstream.response_codes import response_codes

log = logging.getLogger('beanstream.transaction')


class Transaction(object):

    URLS = {
        'process_transaction'   : 'https://www.beanstream.com/scripts/process_transaction.asp',
        'recurring_billing'     : 'https://www.beanstream.com/scripts/recurring_billing.asp',
        'payment_profile'       : 'https://www.beanstream.com/scripts/payment_profile.asp',
        'report_download'       : 'https://www.beanstream.com/scripts/report_download.asp',
        'report'                : 'https://www.beanstream.com/scripts/report.aspx',
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
        self.response_class = Response

        self.params = {}

        if self.beanstream.USERNAME_VALIDATION:
            self.params['username'] = self.beanstream.username
            self.params['password'] = self.beanstream.password

        self._generate_order_number()
        self.params['trnOrderNumber'] = self.order_number
        self.response_params = []

    def validate(self):
        pass

    def commit(self):
        self.validate()

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

        response = self.parse_raw_response(body)
        log.debug('Beanstream response: %s', body)
        log.debug(response)

        return self.response_class(response, *self.response_params)

    def parse_raw_response(self, body):
        return urlparse.parse_qs(body)

    def _generate_order_number(self):
        """ Generate a random 30-digit alphanumeric string.
        """
        self.order_number = ''.join((random.choice(string.ascii_lowercase + string.digits) for x in xrange(30)))

    def _process_amount(self, amount):
        decimal_amount = decimal.Decimal(amount)
        return str(decimal_amount.quantize(decimal.Decimal('1.00')))

    def set_card(self, card):
        if self.beanstream.REQUIRE_CVD and not card.has_cvd():
            log.error('CVD required')
            raise errors.ValidationException('CVD required')

        self.params.update(card.params())
        self.has_credit_card = True

    def set_billing_address(self, address):
        self.params.update(address.params('ord'))
        self.has_billing_address = True

    def set_refs(self, refs):
        if len(refs) > 5:
            raise errors.ValidationException('too many ref fields')

        for ref_idx, ref in enumerate(refs, start=1):
            if ref:
                self.params['ref%s' % ref_idx] = ref


class Response(object):

    def __init__(self, resp_dict):
        self.resp = resp_dict

    def __repr__(self):
        return '%s(%s)' % (self.__class__, self.resp)

    def __str__(self):
        return '%s <transaction_id: %s, order_number: %s>' % (self.__class__, self.transaction_id(), self.order_number())

    def order_number(self):
        ''' Order number assigned in the transaction request. '''
        return self.resp.get('trnOrderNumber', [None])[0]

    def transaction_id(self):
        ''' Beanstream transaction identifier '''
        return self.resp.get('trnId', [None])[0]

    def refs(self):
        return [
            self.resp.get('ref1', [None])[0],
            self.resp.get('ref2', [None])[0],
            self.resp.get('ref3', [None])[0],
            self.resp.get('ref4', [None])[0],
            self.resp.get('ref5', [None])[0],
        ]

