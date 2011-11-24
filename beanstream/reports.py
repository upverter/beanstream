import logging
import re

from beanstream import errors, transaction

log = logging.getLogger('beanstream.reports')


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
                    if m.groups()[idx] == '\x00':
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


class TransactionReportResponse(ReportResponse):

    @classmethod
    def _fields(cls):
        return ['merchant_id', 'merchant_name', 'trn_id', 'trn_datetime',
                'trn_card_owner', 'trn_ip', 'trn_type', 'trn_amount',
                'trn_original_amount', 'trn_returns', 'trn_order_number',
                'trn_batch_number', 'trn_auth_code', 'trn_card_type',
                'trn_adjustment_to', 'trn_response', 'message_id', 'b_name',
                'b_email', 'b_phone', 'b_address1', 'b_address2', 'b_city',
                'b_province', 'b_postal', 'b_country', 's_name', 's_email',
                's_phone', 's_address1', 's_address2', 's_city', 's_province',
                's_postal', 's_country', 'eci', 'eft_rejected', 'eft_returned',
                'avs_response', 'cvd_response', 'trn_currency']


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

