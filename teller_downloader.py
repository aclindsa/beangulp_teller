#!/usr/bin/env python3

from teller_client import Teller
import argparse
import json
from os import path
from datetime import date


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', type=str, required=True,
                        dest="access_token", help="Access token to account")
    parser.add_argument('--cert', type=str, required=True,
                        help="path to the TLS certificate")
    parser.add_argument('--cert-key', type=str, required=True,
                        help="path to the TLS certificate private key")
    parser.add_argument('--account-name', type=str, required=True, help="name of account to retrieve")
    parser.add_argument('--account-id', type=str, required=True, help="account id to retrieve")
    parser.add_argument('--directory', required=True,
                        help="Directory to store downloaded plaid files")
    parser.add_argument('--count', type=int, default=50, help="The maximum number of transactions to return")
    parser.add_argument('--from-id', type=str, default=None,
                        help="The transaction from where to start the page. The first transaction in the API response will be the one immediately before the transaction in the ledger with this id.")
    return parser.parse_args()


class DateEncoder(json.JSONEncoder):
    def default(self, z):
        if isinstance(z, date):
            return (str(z))
        else:
            return super().default(z)


class TellerDownloader:
    def __init__(self, name, teller_cert, teller_key, access_token, account_id, max_transactions=50, from_id=None):
        self.account_name = name
        self.cert = (teller_cert, teller_key)
        self.access_token = access_token
        self.account_id = account_id
        self.max_transactions = max_transactions
        self.from_id = from_id

    def download(self, filename):
        client = Teller(self.cert, self.access_token)
        account_id = self.account_id

        output = {}
        output['teller-version'] = '0.1'

        accounts = client.list_accounts()
        accounts.raise_for_status()
        account = None

        for account in accounts.json():
            if account['id'] == account_id:
                output['accounts'] = account
                break
        if account is None:
            return False

        balances = client.get_account_balances(account_id)
        balances.raise_for_status()
        output['balances'] = balances.json()

        transactions = client.list_account_transactions(account_id, self.max_transactions, self.from_id)
        transactions.raise_for_status()
        output['transactions'] = transactions.json()

        with open(filename, 'w') as out_file:
            json.dump(output, out_file, indent=2, cls=DateEncoder)

        return True

    def filename_suffix(self):
        return "teller.json"

    def name(self):
        return self.account_name

def main(args):
    json_file = path.join(args.directory, f"{date.today()}_{args.account_name}.json")
    downloader = TellerDownloader(account_name=args.account_name,
                                  teller_cert=args.cert,
                                  teller_key=args.cert_key,
                                  access_token=args.access_token,
                                  max_transactions=args.count,
                                  from_id=args.from_id)
    downloader.download(json_file)


if __name__ == "__main__":
    args = _parse_args()
    main(args)
