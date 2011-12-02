from datetime import datetime
import logging

from beanstream import errors, transaction
from beanstream.response_codes import response_codes

log = logging.getLogger('beanstream.process_transaction')

class Purchase(transaction.Transaction):

    def __init__(self, beanstream_gateway, amount):
        super(Purchase, self).__init__(beanstream_gateway)
        self.url = self.URLS['process_transaction']
        self.response_class = PurchaseResponse

        self.params['merchant_id'] = self.beanstream.merchant_id
        self.params['trnAmount'] = self._process_amount(amount)
        self.params['requestType'] = 'BACKEND'
        self.params['trnType'] = self.TRN_TYPES['purchase']

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

    def set_customer_code(self, customer_code):
        self.params['customerCode'] = customer_code
        self.has_customer_code = True

    def set_shipping_details(self, shipping_details):
        pass

    def set_product_details(self, product_details):
        pass

    def set_comments(self, comments):
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


class PurchaseResponse(transaction.Response):

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

    def transaction_id(self):
        return self.resp.get('trnId', [None])[0]

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
        ''' The date and time that the transaction was processed, as a datetime object. '''
        if 'trnDate' in self.resp:
            return datetime.strptime(self.resp['trnDate'][0], '%m/%d/%Y %I:%M:%S %p')
        else:
            return None

    def approved(self):
        ''' Boolean if the transaction was approved or not '''
        return self.resp.get('trnApproved', ['0'])[0] == '1'

    def auth_code(self):
        ''' if the transaction is approved this parameter will contain a unique bank-issued code '''
        return self.resp.get('authCode', [None])[0]


class PreAuthorization(Purchase):

    def __init__(self, beanstream_gateway, amount):
        super(PreAuthorization, self).__init__(beanstream_gateway, amount)

        self.params['trnType'] = self.TRN_TYPES['preauth']


class Adjustment(transaction.Transaction):

    RETURN = 'R'
    VOID = 'V'
    PREAUTH_COMPLETION = 'PAC'
    VOID_RETURN = 'VR'
    VOID_PURCHASE = 'VP'

    def __init__(self, beanstream_gateway, adjustment_type, transaction_id, amount):
        super(PreAuthorizationCompletion, self).__init__(beanstream_gateway)

        if not beanstream_gateway.HASH_VALIDATION and not beanstream_gateway.USERNAME_VALIDATION:
            raise errors.ConfigurationException('adjustments must be performed with either hash or username/password validation')

        if adjustment_type not in [self.RETURN, self.VOID, self.PREAUTH_COMPLETION, self.VOID_RETURN, self.VOID_PURCHASE]:
            raise errors.ConfigurationException('invalid adjustment_type specified: %s' % adjustment_type)

        self.params['trnType'] = adjustment_type
        self.params['adjId'] = transaction_id
        self.params['trnAmount'] = self._process_amount(amount)

