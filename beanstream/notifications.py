#!/usr/bin/python2
'''
Copyright 2012 Upverter Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

from beanstream import transaction, utilities
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
        if 'billingDate' in self.resp:
            return utilities.process_date(self.resp['billingDate'][0])
        else:
            return None

    def billing_period(self):
        return self.resp.get('billingPeriod', [None])[0]

    def billing_increment(self):
        return self.resp.get('billingIncrement', [None])[0]

    def period_from(self):
        if 'periodFrom' in self.resp:
            return utilities.process_date(self.resp['periodFrom'][0])
        else:
            return None

    def period_to(self):
        if 'periodTo' in self.resp:
            return utilities.process_date(self.resp['periodTo'][0])
        else:
            return None

