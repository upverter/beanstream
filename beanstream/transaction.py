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

        response = urlparse.parse_qs(body)
        log.debug('Beanstream response: %s', body)
        log.debug(response)

        return self.response_class(response)

    def _generate_order_number(self):
        """ Generate a random 30-digit alphanumeric string.
        """
        self.order_number = ''.join((random.choice(string.ascii_lowercase + string.digits) for x in xrange(30)))

    def _process_amount(self, amount):
        decimal_amount = decimal.Decimal(amount)
        return str(decimal_amount.quantize(decimal.Decimal('1.00')))

    def add_billing_address(self, address):
        self.params.update(address.params('ord'))
        self.has_billing_address = True

    def add_refs(self, refs):
        if len(refs) > 5:
            raise errors.ValidationException('too many ref fields')

        for ref_idx, ref in enumerate(refs, start=1):
            if ref:
                self['ref%s' % ref_idx] = ref


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


class Purchase(Transaction):

    def __init__(self, beanstream_gateway, amount):
        super(Purchase, self).__init__(beanstream_gateway)
        self.url = self.URLS['process_transaction']
        self.response_class = PurchaseResponse

        self.params['merchant_id'] = self.beanstream.merchant_id
        self.params['trnAmount'] = self._process_amount(amount)
        self.params['requestType'] = 'BACKEND'
        self.params['trnType'] = Transaction.TRN_TYPES['purchase']

        self.has_billing_address = False
        self.has_credit_card = False
        self.has_customer_code = False

    def validate(self):
        if (self.has_billing_address or self.has_credit_card) and self.has_customer_code:
            log.error('billing address or credit card specified with customer code')
            raise errors.ValidationException('cannot specify both customer code and billing address/credit card')

        if not self.has_customer_code and self.beanstream.REQUIRE_BILLING_ADDRESS and not self.has_billing_address:
            log.error('billing address required')
            raise errors.ValidationException('billing address required')

    def add_card(self, card):
        if self.beanstream.REQUIRE_CVD and not card.has_cvd():
            log.error('CVD required')
            raise errors.ValidationException('CVD required')

        self.params.update(card.params())
        self.has_credit_card = True

    def add_customer_code(self, customer_code):
        self.params['customerCode'] = customer_code
        self.has_customer_code = True

    def add_shipping_details(self, shipping_details):
        pass

    def add_product_details(self, product_details):
        pass

    def add_comments(self, comments):
        self.params['trnComments'] = comments

    def set_language(self, language):
        language = language.upper()
        if language not in ('ENG', 'FRE'):
            raise errors.ValidationException('invalid language option specified: %s (must be one of FRE, ENG)' % language)
        self.params['trnLanguage'] = language

    def set_ip_address(self, ip_address):
        if not self.beanstream.HASH_VALIDATION and not self.beanstream.USERNAME_VALIDATION:
            log.warn('IP address must be used with either hash or username/password validation; ignoring')
        else:
            self.params['customerIP'] = ip_address


class PurchaseResponse(Response):

    def cvd_status(self):
        cvd_statuses = {'1': 'CVD Match',
                        '2': 'CVD Mismatch',
                        '3': 'CVD Not Verified',
                        '4': 'CVD Should have been present',
                        '5': 'CVD Issuer unable to process request',
                        '6': 'CVD Not Provided',
                        }
        if 'cvdId' in self.resp:
            return cvd_statuses[self.resp['cvdId'][0]]
        else:
            return None

    def get_cardholder_message(self):
        if 'messageId' in self.resp:
            return response_codes[self.resp['messageId'][0]]['cardholder_message']
        else:
            return None

    def get_merchant_message(self):
        if 'messageId' in self.resp:
            return response_codes[self.resp['messageId'][0]]['merchant_message']
        else:
            return None

    def transaction_amount(self):
        ''' The amount the transaction was for. '''
        return self.resp.get('trnAmount', [None])[0]

    def transaction_datetime(self):
        ''' The date and time that the transaction was processed. '''
        return self.resp.get('trnDate', [None])[0]

    def approved(self):
        ''' Boolean if the transaction was approved or not '''
        return self.resp.get('trnApproved', ['0'])[0] == '1'

    def auth_code(self):
        ''' if the transaction is approved this parameter will contain a unique bank-issued code '''
        return self.resp.get('authCode', [None])[0]

