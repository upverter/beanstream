import logging

from beanstream import errors, transaction
from beanstream.response_codes import response_codes

log = logging.getLogger('beanstream.payment_profiles')


class CreatePaymentProfile(transaction.Transaction):

    def __init__(self, beanstream, card):
        super(CreatePaymentProfile, self).__init__(beanstream)
        self.url = self.URLS['payment_profile']
        self.response_class = CreatePaymentProfileResponse

        if not self.beanstream.payment_profile_passcode:
            raise errors.ConfigurationException('payment profile passcode must be specified to create payment profiles')

        self.params['serviceVersion'] = '1.0'
        self.params['merchantId'] = self.beanstream.merchant_id
        self.params['operationType'] = 'N'
        self.params['passCode'] = self.beanstream.payment_profile_passcode
        self.params['responseFormat'] = 'QS'

        self._generate_order_number()
        self.params['trnOrderNumber'] = self.order_number

        self.params.update(card.params())

    def add_customer_code(self, customer_code):
        self.params['customerCode'] = customer_code

    def set_language(self, language):
        language = language.upper()
        if language not in ('ENG', 'FRE'):
            raise errors.ValidationException('invalid language option specified: %s (must be one of FRE, ENG)' % language)
        self.params['trnLanguage'] = language

    def set_velocity_id(self, velocity_id):
        self.params['velocityIdentity'] = velocity_id

    def set_status_id(self, status_id):
        self.params['statusIdentity'] = status_id


class CreatePaymentProfileResponse(transaction.Response):

    def get_message(self):
        return self.resp.get('responseMessage', [None])[0]

    def customer_code(self):
        return self.resp.get('customerCode', [None])[0]

    def order_number(self):
        return self.resp.get('trnOrderNumber', [None])[0]

    def approved(self):
        return self.resp.get('trnApproved', ['0'])[0] == '1'

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


