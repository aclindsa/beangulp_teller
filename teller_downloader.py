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
    parser.add_argument('--account-id', type=str, required=True, help="account id to retrieve")
    parser.add_argument('--directory', required=True,
                        help="Directory to store downloaded plaid files")
    parser.add_argument('--count', type=int, default=None, help="The maximum number of transactions to return")
    parser.add_argument('--from-id', type=str, default=None,
                        help="The transaction from where to start the page. The first transaction in the API response will be the one immediately before the transaction in the ledger with this id.")
    return parser.parse_args()


class DateEncoder(json.JSONEncoder):
    def default(self, z):
        if isinstance(z, date):
            return (str(z))
        else:
            return super().default(z)


def main(args):
    cert = (args.cert, args.cert_key)
    client = Teller(cert, args.access_token)
    account_id = args.account_id
    count = args.count
    from_id = args.from_id

    output = {}
    output['teller-version'] = '0.1'

    accounts = client.list_accounts()
    accounts.raise_for_status()
    account = None
    for account in accounts.json():
        if account['id'] == account_id:
            output['accounts'] = account
            break

    account_name = f"{account['institution']['name']}_{account['name']}".replace(' ', '_')
    print(f"Downloading {account_name}")

    balances = client.get_account_balances(account_id)
    balances.raise_for_status()
    output['balances'] = balances.json()

    transactions = client.list_account_transactions(account_id, count, from_id)
    transactions.raise_for_status()
    output['transactions'] = transactions.json()

    json_file = path.join(args.directory, f"{date.today()}_{account_name}.json")
    with open(json_file, 'w') as out_file:
        json.dump(output, out_file, cls=DateEncoder)


if __name__ == "__main__":
    args = _parse_args()
    main(args)
