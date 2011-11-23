import logging
import re

from beanstream import errors, process_transaction, transaction

log = logging.getLogger('beanstream.recurring_billing')


class CreateRecurringBillingAccount(process_transaction.Purchase):
    """ Creating a recurring billing account is essentially doing a purchase
    transaction with some options specifying recurring billing.
    """

    def __init__(self, beanstream, amount, frequency_period,
            frequency_increment):
        """ Create a new recurring billing account creation transaction.

        Arguments:
            beanstream: gateway object
            amount: the amount to charge on a recurring basis
            frequency_period: one of DWMY; used in combination with
                frequency_increment to set billing frequency
            frequency_increment: numeric; used in combination with
                frequency_period to set billing frequency
        """

        super(CreateRecurringBillingAccount, self).__init__(beanstream, amount)
        self.response_class = CreateRecurringBillingAccountResponse

        self.params['trnRecurring'] = '1'

        frequency_period = frequency_period.upper()
        if frequency_period not in 'DWMY':
            raise errors.ValidationException('invalid frequency period specified: %s (must be one of DWMY)' % frequency_period)
        self.params['rbBillingPeriod'] = frequency_period

        self.params['rbBillingIncrement'] = frequency_increment

    def set_end_month(self, on):
        if self.params['rbBillingPeriod'] != 'M':
            log.warning('cannot set end_month attribute if billing period is not monthly')
            return

        self.params['rbEndMonth'] = '1' if on else '0'

    def set_delay_charge(self, on):
        self.params['rbCharge'] = '0' if on else '1'

    def set_first_date(self, first_date):
        self.params['rbFirstBilling'] = first_date.strftime('%m%d%Y')

    def set_second_date(self, second_date):
        self.params['rbSecondBilling'] = second_date.strftime('%m%d%Y')

    def set_expiry(self, expiry):
        self.params['rbExpiry'] = expiry.strftime('%m%d%Y')

    def set_tax1(self, on):
        self.params['rbApplyTax1'] = '1' if on else '0'

    def set_tax2(self, on):
        self.params['rbApplyTax2'] = '1' if on else '0'

    def set_taxes(self, on):
        self.set_tax1(on)
        self.set_tax2(on)


class CreateRecurringBillingAccountResponse(process_transaction.PurchaseResponse):

    def account_id(self):
        ''' The account id for the recurring billing account. '''
        return self.resp.get('rbAccountId', [None])[0]


class ModifyRecurringBillingAccount(transaction.Transaction):

    def __init__(self, beanstream, account_id):
        super(ModifyRecurringBillingAccount, self).__init__(beanstream)
        self.url = self.URLS['recurring_billing']
        self.response_class = ModifyRecurringBillingAccountResponse

        if not self.beanstream.recurring_billing_passcode:
            raise errors.ConfigurationException('recurring billing passcode must be specified to modify recurring billing accounts')

        self.params['merchantId'] = self.beanstream.merchant_id
        self.params['serviceVersion'] = '1.0'
        self.params['operationType'] = 'M'
        self.params['passcode'] = self.beanstream.recurring_billing_passcode
        self.params['responseFormat'] = 'QS'

        self.params['rbAccountId'] = account_id

    def parse_raw_response(self, body):
        pattern = re.compile(r'^<\?xml version="1\.0".*>\s*<response>\s*<accountId>([^<]+)</accountId>\s*<code>(\d+)</code>\s*<message>(.*)</message>\s*</response>\s*$')

        m = pattern.match(body)
        if m:
            account_id, response_code, message = m.groups()

            return {
                'accountId': [account_id],
                'code': [response_code],
                'message': [message]
            }

        else:
            raise errors.ValidationException('unexpected message format received: %s' % body)

    def set_amount(self, amount):
        self.params['Amount'] = self._process_amount(amount)

    def set_billing_state(self, billing_state):
        billing_state = billing_state.upper()
        if billing_state not in 'ACO':
            raise errors.ValidationException('invalid billing state specified: %s (must be one of ACO)' % billing_state)

        self.params['rbBillingState'] = billing_state

    def set_comments(self, comments):
        self.params['trnComments'] = comments

    def set_first_date(self, first_date):
        self.params['rbFirstBilling'] = first_date.strftime('%m%d%Y')

    def set_second_date(self, second_date):
        self.params['rbSecondBilling'] = second_date.strftime('%m%d%Y')

    def set_expiry(self, expiry):
        self.params['rbExpiry'] = expiry.strftime('%m%d%Y')

    def set_frequency_period(self, frequency_period):
        frequency_period = frequency_period.upper()
        if frequency_period not in 'DWMY':
            raise errors.ValidationException('invalid frequency period specified: %s (must be one of DMWY)' % frequency_period)

        self.params['rbBillingPeriod'] = frequency_period

    def set_frequency_increment(self, frequency_increment):
        self.params['rbBillingIncrement'] = frequency_increment

    def set_tax1(self, on):
        self.params['rbApplyTax1'] = '1' if on else '0'

    def set_tax2(self, on):
        self.params['rbApplyTax2'] = '1' if on else '0'

    def set_taxes(self, on):
        self.set_tax1(on)
        self.set_tax2(on)

    def set_end_month(self, on):
        if self.params['rbBillingPeriod'] != 'M':
            log.warning('cannot set end_month attribute if billing period is not monthly')
            return

        self.params['rbBillingEndMonth'] = '1' if on else '0'

    def set_never_expires(self, on):
        self.params['rbNeverExpires'] = '1' if on else '0'

    def set_process_back_payments(self, on):
        self.params['processBackPayments'] = '1' if on else '0'


class ModifyRecurringBillingAccountResponse(transaction.Response):

    def approved(self):
        return self.resp.get('code', [0])[0] == '1'

    def message(self):
        return self.resp.get('message', [None])[0]

