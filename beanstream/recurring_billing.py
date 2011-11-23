import logging

from beanstream import errors, transaction

log = logging.getLogger('beanstream.recurring_billing')


class CreateRecurringBillingAccount(transaction.Purchase):
    """ Creating a recurring billing account is essentially doing a purchase
    transaction with some options specifying recurring billing.
    """

    def __init__(self, beanstream, amount, card, frequency_period,
            frequency_increment):
        """ Create a new recurring billing account creation transaction.

        Arguments:
            beanstream: gateway object
            amount: the amount to charge on a recurring basis
            card: the CreditCard object to charge
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

        self.set_card(card)

    def validate(self):
        if not self.has_billing_address:
            raise errors.ValidationException('recurring billing creation requires a billing address')

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


class CreateRecurringBillingAccountResponse(transaction.PurchaseResponse):

    def account_id(self):
        ''' The account id for the recurring billing account. '''
        return self.resp.get('rbAccountId', [None])[0]


class ModifyRecurringBillingAccount(transaction.Transaction):

    def __init__(self, beanstream):
        super(ModifyRecurringBillingAccount, self).__init__(beanstream)
        self.url = self.URLS['recurring_billing']

        self.params['merchantId'] = self.beanstream.merchant_id
        self.params['serviceVersion'] = '1.0'
        self.params['operationType'] = 'M'

