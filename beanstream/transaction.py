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

        return self.response_class(response)

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

    def __init__(self, beanstream_gateway, amount, card, email,
            billing_address=None, shipping_details=None, product_details=None,
            language='ENG', refs=[], comments=None, ip_address=None):
        super(Purchase, self).__init__(beanstream_gateway)
        self.url = self.URLS['process_transaction']
        self.response_class = PurchaseResponse

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

        if shipping_details:
            self._process_shipping_details(shipping_details)

        if product_details:
            self._process_product_details(product_details)

        language = language.upper()
        if language not in ('ENG', 'FRE'):
            raise errors.ValidationException('invalid language option specified: %s (must be one of FRE, ENG)' % language)
        self.params['trnLanguage'] = language

        if refs:
            if len(refs) > 5:
                raise errors.ValidationException('too many ref fields')

            for ref_idx, ref in enumerate(refs, start=1):
                if ref:
                    self['ref%s' % ref_idx] = ref

        if comments:
            self.params['trnComments'] = comments

        if ip_address:
            if not self.beanstream.HASH_VALIDATION and not self.beanstream.USERNAME_VALIDATION:
                log.warn('IP address must be used with either hash or username/password validation; ignoring')
            else:
                self.params['customerIP'] = ip_address

    def _process_shipping_details(self, shipping_details):
        pass

    def _process_product_details(self, product_details):
        pass


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


class CreateRecurringBillingAccount(Purchase):
    """ Creating a recurring billing account is essentially doing a purchase
    transaction with some options specifying recurring billing.
    """

    def __init__(self, beanstream, amount, card, email, frequency_period,
            frequency_increment, end_month=False, delay_charge=False,
            first_date=None, second_date=None, expiry=None, apply_tax1=False,
            apply_tax2=False, billing_address=None, shipping_details=None,
            product_details=None, language='ENG', refs=[], comments=None,
            ip_address=None):
        """ Create a new recurring billing account creation transaction.

        Arguments:
            beanstream: gateway object
            amount: the amount to charge on a recurring basis
            card: the CreditCard object to charge
            email: the email address to which to send receipts
            frequency_period: one of DWMY; used in combination with
                frequency_increment to set billing frequency
            frequency_increment: numeric; used in combination with
                frequency_period to set billing frequency
            end_month: True if the customer should be charged on the last day
                of the month; frequency_period must be M (ignored otherwise)
                (optional)
            delay_charge: True to delay charging until the first billing date;
                False to charge now (optional; default False)
            first_date: a date object containing the first billing date
                (optional)
            second_date: a date object containing the second billing date
                (optional)
            expiry: a date object containing the expiry date of the account
                (optional)
            apply_tax1: True to apply GST or custom tax 1 (optional; default
                False)
            apply_tax2: True to apply PST or custom tax 2 (optional; default
                False)
            billing_address: the billing address associated with the card
                (optional)
            shipping_details: the shipping details associated with the order
                (optional)
            product_details: the product details associated with the order
                (optional)
            language: the preferred language of the email receipts (optional;
                default ENG)
            refs: a list custom order information, maximum length 5 (optional)
            comments: comments associated with the order (optional)
            ip_address: the IP address associated with the order (optional)
        """

        super(CreateRecurringBillingAccount, self).__init__(beanstream, amount,
                card, email, billing_address=billing_address,
                shipping_details=shipping_details,
                product_details=product_details, language=language, refs=refs,
                comments=comments, ip_address=ip_address)
        self.response_class = CreateRecurringBillingAccountResponse

        self.params['trnRecurring'] = '1'

        frequency_period = frequency_period.upper()
        if frequency_period not in 'DWMY':
            raise errors.ValidationException('invalid frequency period specified: %s (must be one of DWMY)' % frequency_period)
        self.params['rbBillingPeriod'] = frequency_period

        self.params['rbBillingIncrement'] = frequency_increment

        if frequency_period == 'M':
            self.params['rbEndMonth'] = '1' if end_month else '0'
        self.params['rbCharge'] = '0' if delay_charge else '1'

        if first_date:
            self.params['rbFirstBilling'] = first_date.strftime('%m%d%Y')
        if second_date:
            self.params['rbSecondBilling'] = second_date.strftime('%m%d%Y')
        if expiry:
            self.params['rbExpiry'] = expiry.strftime('%m%d%Y')

        self.params['rbApplyTax1'] = '1' if apply_tax1 else '0'
        self.params['rbApplyTax2'] = '1' if apply_tax2 else '0'


class CreateRecurringBillingAccountResponses(PurchaseResponse):

    def account_id(self):
        ''' The account id for the recurring billing account. '''
        return self.resp.get('rbAccountId', [None])[0]


class ModifyRecurringBillingAccount(Transaction):

    def __init__(self, beanstream):
        super(ModifyRecurringBillingAccount, self).__init__(beanstream)
        self.url = self.URLS['recurring_billing']

        self.params['merchantId'] = self.beanstream.merchant_id
        self.params['serviceVersion'] = '1.0'
        self.params['operationType'] = 'M'

