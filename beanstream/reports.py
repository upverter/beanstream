import logging
import re

from beanstream import billing, errors, transaction

log = logging.getLogger('beanstream.reports')

TRANSACTION_TYPES = {
        'P' : 'purchase',
        'PA' : 'pre-authorization',
        'PAC' : 'pre-authorization completion',
        'R' : 'return',
        'VP' : 'void purchase',
        'VR' : 'void return',
}


class Report(transaction.Transaction):

    def __init__(self, beanstream):
        super(Report, self).__init__(beanstream)
        self.url = self.URLS['report_download']
        self.response_class = ReportResponse

        self.params['merchantId'] = self.beanstream.merchant_id
        self.params['loginCompany'] = self.beanstream.login_company
        self.params['loginUser'] = self.beanstream.login_user
        self.params['loginPass'] = self.beanstream.login_password

        self.params['rptFormat'] = 'TAB'
        self.params['rspFormat'] = 'NVP'
        self.params['rptTarget'] = 'INLINE'

    def parse_raw_response(self, body):
        fields = self.response_class._fields()

        lines = body.split('\r\n')

        report = []
        pattern = re.compile(r'\t'.join([r'([^\t]*)'] * len(fields)))
        for line in lines[1:]:
            m = pattern.match(line)
            if not line.strip():
                continue

            if m:
                report_item = {}
                for idx, field in enumerate(fields):
                    if not m.groups()[idx] or m.groups()[idx] == '\x00':
                        report_item[field] = None
                    else:
                        report_item[field] = m.groups()[idx]
                report.append(report_item)

            else:
                raise errors.ValidationException('unexpected format received: %s' % line)

        return report


class ReportResponse(transaction.Response):

    @classmethod
    def _fields(cls):
        return []

    def items(self):
        return self.resp


class TransactionReport(Report):

    def __init__(self, beanstream):
        super(TransactionReport, self).__init__(beanstream)
        self.response_class = TransactionReportResponse

        self.params['rptVersion'] = '1.6'
        self.params['rptNoFile'] = '1'

    def set_transaction_range(self, start, end):
        self.params['rptRange'] = '1'
        self.params['rptIdStart'] = start
        self.params['rptIdEnd'] = end

    def set_date_range(self, start, end):
        self.params['rptStartYear'] = start.strftime('%Y')
        self.params['rptStartMonth'] = start.strftime('%m')
        self.params['rptStartDay'] = start.strftime('%d')

        self.params['rptEndYear'] = end.strftime('%Y')
        self.params['rptEndMonth'] = end.strftime('%m')
        self.params['rptEndDay'] = end.strftime('%d')

    def set_batch_number(self, batch_number):
        self.params['rptBatchNumber'] = batch_number

    def set_status(self, approved=True, declined=True):
        if not approved and not declined:
            log.warning('weird status request for not approved and not declined; ignoring')
            return

        if approved and declined:
            self.params['rptStatus'] = '0'

        elif approved and not declined:
            self.params['rptStatus'] = '1'

        elif declined and not approved:
            self.params['rptStatus'] = '2'

    def set_card_type(self, card_type):
        if card_type not in ('VI', 'MC', 'NN', 'AM', 'DI', 'CB', 'JB'):
            log.error('unexpected card type: %s', card_type)

        self.params['rptCardType'] = card_type

    def set_transaction_type(self, credit_card=True, direct_payment=True):
        if not credit_card and not direct_payment:
            log.warning('weird transaction type request for not credit card and not direct payment; ignoring')
            return

        if credit_card and direct_payment:
            self.params['rptTransTypes'] = '3'

        elif credit_card and not direct_payment:
            self.params['rptTransTypes'] = '1'

        elif direct_payment and not credit_card:
            self.params['rptTransTypes'] = '2'

    def set_include_refs(self, include_refs):
        if include_refs:
            self.params['rptRef'] = 1
        elif 'rptRef' in self.params:
            del self.params['rptRef']


class TransactionReportResponse(object):

    @classmethod
    def _fields(cls):
        return ['merchant_id', 'merchant_name', 'transaction_id',
                'transaction_datetime', 'transaction_card_owner',
                'transaction_ip', 'transaction_type', 'transaction_amount',
                'transaction_original_amount', 'transaction_returns',
                'transaction_order_number', 'transaction_batch_number',
                'transaction_auth_code', 'transaction_card_type',
                'transaction_adjustment_to', 'transaction_response',
                'message_id', 'billing_name', 'billing_email', 'billing_phone',
                'billing_address1', 'billing_address2', 'billing_city',
                'billing_province', 'billing_postal', 'billing_country',
                'shipping_name', 'shipping_email', 'shipping_phone',
                'shipping_address1', 'shipping_address2', 'shipping_city',
                'shipping_province', 'shipping_postal', 'shipping_country',
                'eci', 'eft_rejected', 'eft_returned', 'avs_response',
                'cvd_response', 'transaction_currency']

    def __init__(self, report):
        self.report = report

        # do some additional post-processing.
        for item in report:
            # parse out the billing & shipping addresses.
            self._process_address(item, 'billing')
            self._process_address(item, 'shipping')

            self._process_transaction_type(item)

    def _process_address(self, item, key_prefix):
        fields = ['_name', '_email', '_phone', '_address1', '_address2',
                '_city', '_province', '_postal', '_country']
        if item['%s_name' % key_prefix] and item['%s_email' % key_prefix]:
            address = billing.Address(
                *[item[key_prefix + field] for field in fields])

            item['%s_address' % key_prefix] = address

        for field in fields:
            del item[key_prefix + field]

    def _process_transaction_type(self, item):
        item['transaction_type'] = TRANSACTION_TYPES[item['transaction_type']]

    def __iter__(self):
        return self.report.__iter__()

    def __len__(self):
        return len(self.report)


class TransactionSetReport(TransactionReport):
    """ Specify a set of transaction IDs for which to fetch details. This is
    performed by fetching the range of transaction IDs and then filtering out
    anything that wasn't passed in. """

    def __init__(self, beanstream, transaction_ids):
        super(TransactionSetReport, self).__init__(beanstream)
        self.response_class = TransactionSetReportResponse

        # in case it was passed in as a generator, or as numbers, or both
        transaction_ids = [str(txn_id) for txn_id in transaction_ids]
        transaction_ids.sort()
        self.response_params.append(transaction_ids)

        self.set_transaction_range(transaction_ids[0], transaction_ids[-1])


class TransactionSetReportResponse(TransactionReportResponse):

    def __init__(self, response, transaction_ids):
        super(TransactionSetReportResponse, self).__init__(response)

        # filter out anything that wasn't in the original set.
        report = []
        for item in self.report:
            if item['transaction_id'] in transaction_ids:
                report.append(item)

        self.report = report


class CreditCardLookupReport(Report):

    def __init__(self, beanstream):
        super(CreditCardLookupReport, self).__init__(beanstream)
        self.url = self.URLS['report']

        self.params['rptAPIVersion'] = '1.0'
        self.params['rptType'] = 'SEARCH'

    def validate(self):
        if 'rptTransId' not in self.params and 'rptCcNumber' not in self.params:
            raise errors.ValidationException('CreditCardLookupReport must specify one of transaction id or credit card number')

    def set_transaction_id(self, transaction_id):
        self.params['rptTransId'] = transaction_id

    def set_credit_card_number(self, credit_card_number):
        self.params['rptCcNumber'] = credit_card_number

    def set_datetime_range(self, start, end):
        self.params['rptStartYear'] = start.strftime('%Y')
        self.params['rptStartMonth'] = start.strftime('%m')
        self.params['rptStartDay'] = start.strftime('%d')
        self.params['rptStartHour'] = start.strftime('%H')
        self.params['rptStartMin'] = start.strftime('%M')
        self.params['rptStartSec'] = start.strftime('%S')

        self.params['rptEndYear'] = end.strftime('%Y')
        self.params['rptEndMonth'] = end.strftime('%m')
        self.params['rptEndDay'] = end.strftime('%d')
        self.params['rptEndHour'] = end.strftime('%H')
        self.params['rptEndMin'] = end.strftime('%M')
        self.params['rptEndSec'] = end.strftime('%S')

    def set_status(self, approved=True, declined=True):
        if not approved and not declined:
            log.warning('weird status request for not approved and not declined; ignoring')
            return

        if approved and declined and 'rptTransStatus' in self.params:
            del self.params['rptTransStatus']

        elif approved and not declined:
            self.params['rptTransStatus'] = '1'

        elif declined and not approved:
            self.params['rptTransStatus'] = '2'


class CreditCardLookupReportResponse(ReportResponse):

    def _fields(cls):
        return ['transaction_id', 'date', 'source_ip', 'amount', 'type_id',
                'type_name', 'card_type', 'card_expiry', 'order_id',
                'batch_number', 'status']

