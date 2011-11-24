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

    def __init__(self, name, email, phone, address1, address2, city, province, postal_code, country):
        """ Initialize an address struct and perform some basic validation.
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

        if not address1:
            raise errors.ValidationException('Address1 must be specified in address')
        self.address1 = address1
        self.address2 = address2

        if not city:
            raise errors.ValidationException('City must be specified in address')
        self.city = city

        if not province:
            raise errors.ValidationException('Province/state must be specified in addresss')
        if len(province) != 2:
            raise errors.ValidationException('Malformed province/state code: %s' % province)
        self.province = province

        if not postal_code:
            raise errors.ValidationException('Postal code must be specified in address')
        self.postal_code = postal_code

        if not country:
            raise errors.ValidationException('Country code must be specified in address')
        if len(country) != 2:
            raise errors.ValidationException('Malformed country code: %s' % country)
        self.country = country

    def params(self, key_prefix):
        return {
            '%sName' % key_prefix: self.name,
            '%sEmailAddress' % key_prefix: self.email,
            '%sPhoneNumber' % key_prefix: self.phone,
            '%sAddress1' % key_prefix: self.address1,
            '%sAddress2' % key_prefix: self.address2,
            '%sCity' % key_prefix: self.city,
            '%sProvince' % key_prefix: self.province,
            '%sPostalCode' % key_prefix: self.postal_code,
            '%sCountry' % key_prefix: self.country,
        }

