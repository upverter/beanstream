from beanstream import transaction
from beanstream.response_codes import response_codes


class RecurringBillingNotification(transaction.Response):

    def account_id(self):
        return self.resp.get('billingId', None)

    def approved(self):
        return self.resp.get('trnApproved', '0') == '1'

    def transaction_id(self):
        return self.resp.get('trnId', None)

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
        return self.resp.get('authCode', None)

    def name(self):
        return self.resp.get('accountName', None)

    def email(self):
        return self.resp.get('emailAddress', None)

    def billing_amount(self):
        return self.resp.get('billingAmount', None)

    def billing_date(self):
        return self.resp.get('billingDate', None)

    def billing_period(self):
        return self.resp.get('billingPeriod', None)

    def billing_increment(self):
        return self.resp.get('billingIncrement', None)

    def period_from(self):
        return self.resp.get('periodFrom', None)

    def period_to(self):
        return self.resp.get('periodTo', None)

