from beanstream import transaction
from beanstream.response_codes import response_codes


class RecurringBillingNotification(transaction.Response):

    def __init__(self, *args, **kwargs):
        super(RecurringBillingNotification, self).__init__(*args, **kwargs)

        # listify things if they aren't already listified.
        self.resp = dict((k, [v]) if type(v) != list else (k, v) for k, v in self.resp.iteritems())

    def account_id(self):
        return self.resp.get('billingId', [None])[0]

    def approved(self):
        return self.resp.get('trnApproved', ['0'])[0] == '1'

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

    def auth_code(self):
        return self.resp.get('authCode', [None])[0]

    def name(self):
        return self.resp.get('accountName', [None])[0]

    def email(self):
        return self.resp.get('emailAddress', [None])[0]

    def billing_amount(self):
        return self.resp.get('billingAmount', [None])[0]

    def billing_date(self):
        return self.resp.get('billingDate', [None])[0]

    def billing_period(self):
        return self.resp.get('billingPeriod', [None])[0]

    def billing_increment(self):
        return self.resp.get('billingIncrement', [None])[0]

    def period_from(self):
        return self.resp.get('periodFrom', [None])[0]

    def period_to(self):
        return self.resp.get('periodTo', [None])[0]

