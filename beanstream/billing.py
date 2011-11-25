import calendar
from datetime import date

import errors


class CreditCard:

    def __init__(self, name, number, exp_month, exp_year, cvd=''):
        """ Initialize a credit card struct and perform some basic validation.

        Arguments:
            name: the owner of the credit card, as displayed on the card itself
            number: the number of the credit card
            exp_month: the month of expiry, as a number, 1-indexed
            exp_year: the year of expiry, as a number
            cvd: the CVD of the credit card (optional)
        """
        if not name:
            raise errors.ValidationException('Name must be specified in credit card')
        self.name = name

        if not number:
            raise errors.ValidationException('Number must be specified in credit card')
        self.number = str(number)

        if not exp_month:
            raise errors.ValidationException('Expiry month must be specified in credit card')
        if not exp_year:
            raise errors.ValidationException('Expiry year must be specified in credit card')

        # Parse out the month & year as expected by Beanstream (numeric month,
        # 1-indexed, & last two digits of the year).
        year = int(exp_year)
        month = int(exp_month)
        expiry_date = date(year, month, calendar.monthrange(year, month)[1])
        self.exp_month = expiry_date.strftime('%m')
        self.exp_year = expiry_date.strftime('%y')

        self.cvd = str(cvd)

    def has_cvd(self):
        return bool(self.cvd)

    def params(self):
        return {
            'trnCardOwner': self.name,
            'trnCardNumber': self.number,
            'trnExpMonth': self.exp_month,
            'trnExpYear': self.exp_year,
            'trnCardCvd': self.cvd,
        }


class Address:

    def __init__(self, name, email, phone=None, address1=None, address2=None,
            city=None, province=None, postal_code=None, country=None):
        """ Initialize an address struct.
        """
        if not name:
            raise errors.ValidationException('Name must be specified in address')
        self.name = name

        if not email:
            raise errors.ValidationException('Email must be specified in address')
        self.email = email

        self.phone = None
        if phone:
            self.phone = str(phone)

        self.address1 = address1
        self.address2 = address2
        self.city = city
        self.province = province
        self.postal_code = postal_code
        self.country = country

    def params(self, key_prefix):
        kvs = {
            '%sName' % key_prefix: self.name,
            '%sEmailAddress' % key_prefix: self.email,
        }

        if self.phone:
            kvs['%sPhoneNumber' % key_prefix] = self.phone

        if self.address1:
            kvs['%sAddress1' % key_prefix] = self.address1

        if self.address2:
            kvs['%sAddress2' % key_prefix] = self.address2

        if self.city:
            kvs['%sCity' % key_prefix] = self.city

        if self.province:
            kvs['%sProvince' % key_prefix] = self.province

        if self.postal_code:
            kvs['%sPostalCode' % key_prefix] = self.postal_code

        if self.country:
            kvs['%sCountry' % key_prefix] = self.country

        return kvs

