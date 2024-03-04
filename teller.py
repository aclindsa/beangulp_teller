#!/usr/bin/env python3

from beancount.core import data, amount, position, flags, interpolate
from beancount.core.number import D, ZERO, ONE
from beangulp.testing import main
from datetime import timedelta, date
from dateutil.parser import parse

import beangulp
import collections
import json


class TellerSimilarityComparator:
    """Similarity comparator of imported Plaid transactions.

    This comparator needs to be able to handle Transaction instances which are
    incomplete on one side, which have slightly different dates, or potentially
    slightly different numbers.
    """

    # Fraction difference allowed of variation.
    EPSILON = D('0.05')  # 5%

    def __init__(self, max_date_delta=None):
        """Constructor a comparator of entries.
        Args:
          max_date_delta: A datetime.timedelta instance of the max tolerated
            distance between dates.
        """
        self.cache = {}
        self.max_date_delta = max_date_delta

    def __call__(self, entry1, entry2):
        """Compare two entries, return true if they are deemed similar.

        Args:
          entry1: A first Transaction directive.
          entry2: A second Transaction directive.
        Returns:
          A boolean.
        """
        # Check the date difference.
        if self.max_date_delta is not None:
            delta = ((entry1.date - entry2.date)
                     if entry1.date > entry2.date else
                     (entry2.date - entry1.date))
            if delta > self.max_date_delta:
                return False

        try:
            amounts1 = self.cache[id(entry1)]
        except KeyError:
            amounts1 = self.cache[id(entry1)] = amounts_map(entry1)
        try:
            amounts2 = self.cache[id(entry2)]
        except KeyError:
            amounts2 = self.cache[id(entry2)] = amounts_map(entry2)

        # Look for amounts on common accounts.
        common_keys = set(amounts1) & set(amounts2)
        for key in sorted(common_keys):
            # Compare the amounts.
            number1 = amounts1[key]
            number2 = amounts2[key]
            if number1 == ZERO and number2 == ZERO:
                break
            diff = abs((number1 / number2)
                       if number2 != ZERO
                       else (number2 / number1))
            if diff == ZERO:
                return False
            if diff < ONE:
                diff = ONE/diff
            if (diff - ONE) < self.EPSILON:
                break
        else:
            return False

        return True


def amounts_map(entry):
    """Compute a mapping of (account, currency) -> Decimal balances.

    Args:
      entry: A Transaction instance.
    Returns:
      A dict of account -> Amount balance.
    """
    amounts = collections.defaultdict(D)
    for posting in entry.postings:
        if not posting.meta:
            continue
        # Skip interpolated postings.
        if interpolate.AUTOMATIC_META in posting.meta or 'fin_id' not in posting.meta:
            continue
        currency = isinstance(posting.units, amount.Amount) and posting.units.currency
        if isinstance(currency, str):
            plaid_id = posting.meta['fin_id'] if 'fin_id' in posting.meta else None
            key = (posting.account, plaid_id, currency)
            amounts[key] += posting.units.number
    return amounts


class Importer(beangulp.Importer):
    def __init__(self, account_name, account_id):
        self.account_name = account_name
        self.account_id = account_id

    def identify(self, filepath):
        with open(filepath) as fp:
            try:
                j = json.load(fp)
            except:
                return False

            if 'teller-version' in j and j['teller-version'] == '0.1':
                if 'accounts' in j and j['accounts']['id'] == self.account_id:
                    return True
        return False

    def account(self, filepath):
        return self.account_name

    def filename(self, filepath):
        return f"{self.account_name.split(':')[-1]}.json"

    def extract(self, filepath, existing):
        entries = []
        fp = open(filepath)
        j = json.load(fp)

        currency = j['accounts']['currency']
        acct_type = j['accounts']['type']
        latest_date = date.min

        for index, transaction in enumerate(j['transactions']):
            t_date = parse(transaction['date']).date()
            latest_date = t_date if t_date > latest_date else latest_date

            desc = transaction['description']
            if 'counter_part' in transaction['details']:
                merch = transaction['details']['counterparty']['name']
            else:
                merch = desc
            fin_id = transaction['id']
            amt = transaction['amount']
            meta = data.new_metadata(filepath, index)
            units = amount.Amount(D(amt), currency)

            leg1 = data.Posting(self.account_name, -units, None, None, None,
                                {'fin_id': fin_id})
            txn = data.Transaction(meta, t_date, flags.FLAG_OKAY, merch, desc,
                                   data.EMPTY_SET, data.EMPTY_SET, [leg1])
            entries.append(txn)

        # Insert final balance check
        if len(entries):
            balance = j['balances']['ledger']
            meta = data.new_metadata(filepath, 0)
            amt = amount.Amount(D(balance), currency)
            amt = -amt if acct_type == "credit" else amt
            entries.append(data.Balance(meta, latest_date + timedelta(days=1),
                                        self.account_name, amt, None, None))

        return entries


if __name__ == '__main__':
    importer = Importer('Assets:Current:CitiSampleBank',
                        'acc_os1rm9h3k65vdrb176000')
    main(importer)
