## Beanstream Python API

The goal of this library is to provide a python implementation of the
Beanstream API.

The library supports:

 * payment profiles
 * one off transactions
 * pre-authorizing transactions
 * voiding transactions
 * recurring billing
 * reporting

The library is licensed under the Apache 2.0 license
(http://www.apache.org/licenses/LICENSE-2.0).


## Getting started

The API is interacted with through the Gateway object. The Gateway holds all of
the beanstream account configuration.

    from beanstream import gateway
    beangw = gateway.Beanstream(
        hash_validation=hash_validation,
        require_billing_address=require_billing_address,
        require_cvd=require_cvd)
    beangw.configure(
        merchant_id,
        company,
        username,
        password,
        hashcode=hashcode,
        hash_algorithm=hash_algorithm,
        payment_profile_passcode=payment_profile_passcode,
        recurring_billing_passcode=recurring_billing_passcode)

The `gateway` object has methods for constructing `transaction`s to the
Beanstream API. A `transaction` encapsulates the information involved in a
request against the beanstream API.

Ex. Making a one off transation:

    from beanstream import gateway, billing
    
    beangw = create_gateway()
    card = billing.CreditCard(
        'John Doe',
        '4030000010001234',
        '09', '2015',
        '123')
    
    txn = beangw.purchase(50, card, self.billing_address)
    txn.set_comments('$50 Frobinator for John Doe')
    resp = txn.commit()
    
    if resp.approved():
        ship_frobinator('John Doe')


## Running tests

To run the library test a file named beanstream.cfg in the current directory.
Then run the command `nosetests tests/simple_t.py`.

The tests attempt to make requests against the Beanstream API using the test
credit cards given for sandbox use.

Example config file:
    # these should match your beanstream account settings
    hash_validation: true
    require_billing_address: true
    require_cvd: true
    
    [beanstream]
    merchant_id: xxyyzz
    company: foo corp
    username: foo_user
    password: foo_pass
    hashcode: api_hc
    hash_algorithm: SHA1
    payment_profile_passcode: pp_pass
    recurring_billing_passcode: rb_pass


