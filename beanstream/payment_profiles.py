import logging

from beanstream import billing, errors, transaction
from beanstream.response_codes import response_codes

log = logging.getLogger('beanstream.payment_profiles')


STATUS_DESCRIPTORS = {
        'active' : 'A',
        'closed' : 'C',
        'disabled' : 'D'
}

STATUS_CODES = {
        'A' : 'active',
        'C' : 'closed',
        'D' : 'disabled'
}


class PaymentProfileTransaction(transaction.Transaction):

    def __init__(self, beanstream):
        super(PaymentProfileTransaction, self).__init__(beanstream)
        self.url = self.URLS['payment_profile']
        self.response_class = PaymentProfileResponse

        if not self.beanstream.payment_profile_passcode:
            raise errors.ConfigurationException('payment profile passcode must be specified to create or modify payment profiles')

        self.params['serviceVersion'] = '1.0'
        self.params['merchantId'] = self.beanstream.merchant_id
        self.params['passCode'] = self.beanstream.payment_profile_passcode
        self.params['responseFormat'] = 'QS'

    def set_customer_code(self, customer_code):
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

    def set_status(self, status):
        status = status.lower()

        if status not in STATUS_DESCRIPTORS:
            raise errors.ValidationException('invalid status option specified: %s' % status)

        self.params['status'] = STATUS_DESCRIPTORS[status]

    def set_validation(self, validate):
        self.params['cardValidation'] = '1' if validate else '0'


class CreatePaymentProfile(PaymentProfileTransaction):

    def __init__(self, beanstream, card):
        super(CreatePaymentProfile, self).__init__(beanstream)

        self.params['operationType'] = 'N'
        self.params.update(card.params())


class ModifyPaymentProfile(PaymentProfileTransaction):

    def __init__(self, beanstream, customer_code):
        super(ModifyPaymentProfile, self).__init__(beanstream)

        self.params['operationType'] = 'M'
        self.set_customer_code(customer_code)


class GetPaymentProfile(PaymentProfileTransaction):

    def __init__(self, beanstream, customer_code):
        super(GetPaymentProfile, self).__init__(beanstream)

        self.params['operationType'] = 'Q'
        self.set_customer_code(customer_code)


class PaymentProfileResponse(transaction.Response):

    field_name_mapping = {
        'ordName': 'name',
        'ordAddress1': 'address line 1',
        'ordAddress2': 'address line 2',
        'ordCity': 'city',
        'ordProvince': 'state/province',
        'ordCountry': 'country',
        'ordPostalCode': 'zip/postal code',
        'ordEmailAddress': 'email address',
        'trnCardNumber': 'credit card number',
        'trnCardOwner': 'credit card owner',
        'trnCardExpiry': 'credit card expiry',
        'customerCode': 'customer code',
    }

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

    def get_message(self):
        return self.resp.get('responseMessage', [None])[0]

    def get_errors(self):
        if self.approved():
            return {}

        if not 'responseCode' in self.resp:
            return {'message': 'no response code'}

        if self.resp['responseCode'][0] == '19':
            error_messages = self.resp['errorMessage'][0].split('<br>')[:-1] # last one is always blank
            error_fields = self.resp['errorFields'][0].split(',')

            human_error_fields = [self.field_name_mapping.get(field, 'unknown') for field in error_fields]
            return {'fields': dict(zip(human_error_fields, error_messages))}

        if 'messageId' in self.resp:
            cardholder_message = self.get_cardholder_message()
            return {'message': cardholder_message}

        if 'responseMessage' in self.resp:
            message = self.resp['responseMessage'][0]
            if message == 'DECLINED':
                message = 'Declined'
            return {'message': message}

        return {}

    def customer_code(self):
        return self.resp.get('customerCode', [None])[0]

    def order_number(self):
        return self.resp.get('trnOrderNumber', [None])[0]

    def approved(self):
        return self.resp.get('responseCode', ['0'])[0] == '1' and self.resp.get('trnApproved', ['1'])[0] == '1'

    def status(self):
        if 'status' in self.resp:
            return STATUS_CODES[self.resp['status'][0]]
        else:
            return None

    def billing_address(self):
        return billing.Address(
            self.resp.get('ordName', [None])[0],
            self.resp.get('ordEmailAddress', [None])[0],
            self.resp.get('ordPhoneNumber', [None])[0],
            self.resp.get('ordAddress1', [None])[0],
            self.resp.get('ordAddress2', [None])[0],
            self.resp.get('ordCity', [None])[0],
            self.resp.get('ordProvince', [None])[0],
            self.resp.get('ordPostalCode', [None])[0],
            self.resp.get('ordCountry', [None])[0],
        )

    def bank_account_type(self):
        return self.resp.get('bankAccountType', [None])[0]

    def card_owner(self):
        return self.resp.get('trnCardOwner', [None])[0]

    def card_number(self):
        return self.resp.get('trnCardNumber', [None])[0]

    def expiry_month(self):
        if 'trnCardExpiry' in self.resp:
            return self.resp['trnCardExpiry'][0][:-2]
        else:
            return None

    def expiry_year(self):
        if 'trnCardExpiry' in self.resp:
            return self.resp['trnCardExpiry'][0][-2:]
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

