#!/usr/bin/env python3

import argparse
import requests


class Teller():
    _BASE_URL = 'https://api.teller.io'
    _VERSION = '2020-10-12'

    def __init__(self, cert, access_token=None):
        self.cert = cert
        self.access_token = access_token

    def list_institutions(self):
        return self._get('/institutions')

    # Returns an array of accounts with beneficial owner identity information
    # attached.
    def get_identity(self):
        return self._get('/identity')

    # Returns a list of all accounts the end-user granted access to during
    # enrollment in Teller Connect.
    def list_accounts(self):
        return self._get('/accounts')

    # Retrieve a specific account by it's id.
    def get_account(self, account_id):
        return self._get(f'/accounts/{account_id}')

    # This deletes your application's authorization to access the given
    # account as addressed by its id. This does not delete the account itself.
    # Removing access will cancel billing for subscription billed products
    # associated with the account, e.g. transactions.
    def delete_account(self, account_id):
        return self._delete(f'/accounts/{account_id}')

    # Returns the account's details.
    def get_account_details(self, account_id):
        return self._get(f'/accounts/{account_id}/details')

    # Returns the account's balances.
    def get_account_balances(self, account_id):
        return self._get(f'/accounts/{account_id}/balances')

    # Returns a list of all transactions belonging to the account.
    def list_account_transactions(self, account_id, count=None, from_id=None):
        params = {"count": count}
        if from_id is not None:
            params['from_id'] = from_id
        return self._get(f'/accounts/{account_id}/transactions', params=params)

    # Returns an individual transaction.
    def get_account_transaction(self, account_id, transaction_id):
        return self._get(f'/accounts/{account_id}/transactions/{transaction_id}')

    # TODO: Missing payment support (BETA) Api

    def _get(self, path, params=None):
        return self._request('GET', path, params=params)

    def _delete(self, path):
        return self._request('DELETE', path)

    def _request(self, method, path, params=None, data=None):
        url = self._BASE_URL + path
        auth = (self.access_token, '')
        headers = {'Teller-Version': self._VERSION}
        return requests.request(method, url, json=data, cert=self.cert,
                                params=params, auth=auth, headers=headers)


def _parse_args():
    parser = argparse.ArgumentParser(description="Download banking data from teller")

    parser.add_argument('--token', type=str, required=True,
                        dest="access_token", help="Access token to account")
    parser.add_argument('--cert', type=str, required=True,
                        help="path to the TLS certificate")
    parser.add_argument('--cert-key', type=str, required=True,
                        help="path to the TLS certificate private key")
    subparser = parser.add_subparsers(required=True, dest="command", metavar="COMMAND")

    list_institutions = subparser.add_parser('list-institutions', help="Returns a list of institutions supported by teller")

    get_identity = subparser.add_parser('get-identity', help="Get an array of accounts with beneficial owner identity information attached")

    list_accounts = subparser.add_parser(
        'list-accounts', help="Returns a list of all accounts the end-user granted access to during enrollment in Teller Connect.")

    get_account = subparser.add_parser('get-account', help="Retrieve a specific account by it's id")
    get_account.add_argument('--account-id', type=str, required=True, help="account id to retrieve")

    delete_account = subparser.add_parser('delete-account', help="Delete your account, removing access and cancel billing for associated with this account")
    delete_account.add_argument('--account-id', type=str, required=True, help="account id to delete")

    get_account_details = subparser.add_parser('get-account-details', help="Returns the account's details")
    get_account_details.add_argument('--account-id', type=str, required=True, help="account id to retrieve")

    get_account_balances = subparser.add_parser('get-account-balances', help="Returns the account's balance")
    get_account_balances.add_argument('--account-id', type=str, required=True, help="account id to retrieve")

    list_account_transactions = subparser.add_parser('list-account-transactions', help="Returns a list of all transactions belonging to the account")
    list_account_transactions.add_argument('--account-id', type=str, required=True, help="account id to retrieve")
    list_account_transactions.add_argument('--count', type=int, default=None, help="The maximum number of transactions to return")
    list_account_transactions.add_argument(
        '--from-id', type=str, default=None, help="The transaction from where to start the page. The first transaction in the API response will be the one immediately before the transaction in the ledger with this id.")

    get_account_transaction = subparser.add_parser('get-account-transaction', help="Returns a list of all transactions belonging to the account")
    get_account_transaction.add_argument('--account-id', type=str, required=True, help="account id to retrieve")
    get_account_transaction.add_argument('--transaction-id', type=str, required=True, help="transaction id to retrieve")

    return parser.parse_args()


def main(args):
    cert = (args.cert, args.cert_key)
    client = Teller(cert, args.access_token)
    resp = None

    match args.command:
        case 'list-institutions':
            resp = client.list_institutions()
        case 'get-identity':
            resp = client.get_identity()
        case 'list-accounts':
            resp = client.list_accounts()
        case 'get-account':
            resp = client.get_account(args.account_id)
        case 'delete-account':
            resp = client.delete_account(args.account_id)
        case 'get-account-details':
            resp = client.get_account_details(args.account_id)
        case 'get-account-balances':
            resp = client.get_account_balances(args.account_id)
        case 'list-account-transactions':
            resp = client.list_account_transactions(args.account_id, args.count, args.from_id)
        case 'get-account-transaction':
            resp = client.get_account_transaction(args.account_id, args.transaction_id)
        case _:
            print("Unknown command")

    resp.raise_for_status()
    print(resp.json())


if __name__ == "__main__":
    args = _parse_args()
    main(args)
