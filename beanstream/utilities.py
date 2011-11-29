from datetime import date

def process_date(datestring):
    """ 11/29/2011 --> date(2011, 11, 29) """
    month, day, year = datestring.split('/')
    return date(year, month, day)
