import datetime as dt
import os
import pandas as pd
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

import schema.bank as bank
from schema.bank import Account, Transaction
from utilities.connections import connect_universe
from utilities.queries import query_bank_id, query_last_bank_customer_id


class Bank:
    def __init__(self, starting_capital, bank_name, path='db/banks/', date_established=dt.datetime(1, 12, 31)):
        if not os.path.exists(path):
            os.makedirs(path)
        self.engine = sa.create_engine(
            'sqlite:///' + path + bank_name + '.db',
            echo=True
        )
        session = sessionmaker(bind=self.engine)
        bank.Base.metadata.create_all(self.engine)
        self.session = session()
        self.connection = self.engine.connect()
        self.name = bank_name
        self.date_established = date_established
        self.id = self.__register()
        self.get_customers(self.id, 'bank')
        self.cash_account = self.assign_account(
            customer_id=self.id,
            account_type='cash'
        )
        self.capital_account = self.assign_account(self.id, 'capital')
        self.liability_account = self.assign_account(self.id, 'liability')
        self.make_transaction(
            self.cash_account,
            self.capital_account,
            self.date_established,
            starting_capital
        )

    def __register(self):
        # populate universe company record
        insurer_table = pd.DataFrame([[self.name]], columns=['bank_name'])
        session, connection = connect_universe()
        insurer_table.to_sql(
            'bank',
            connection,
            index=False,
            if_exists='append'
        )
        bank_id = query_bank_id(self.name)
        return bank_id

    def get_customers(self, ids, customer_type):
        new_customers = pd.DataFrame()
        new_customers[customer_type + '_id'] = pd.Series(ids)
        new_customers['customer_type'] = customer_type
        last_id = query_last_bank_customer_id(self.name)
        if last_id is None:
            customer_ids = list(range(new_customers.shape[0] + 1))
            customer_ids.pop(0)
            new_customers['customer_id'] = customer_ids

        else:
            next_id = last_id + 1
            new_customers['customer_id'] = list(range(next_id, next_id + new_customers.shape[0]))

        to_entity = new_customers[[customer_type + '_id', 'customer_id']].copy()
        new_customers = new_customers[['customer_id', 'customer_type']]

        to_entity.to_sql(
            customer_type,
            self.connection,
            index=False,
            if_exists='append'
        )

        new_customers.to_sql(
            'customer',
            self.connection,
            index=False,
            if_exists='append'
        )

    def assign_accounts(self, customer_ids, account_type):
        """
        assign multiple accounts given customer ids
        """
        new_accounts = pd.DataFrame()
        new_accounts['customer_id'] = customer_ids
        new_accounts['account_type'] = account_type

        new_accounts.to_sql(
            'account',
            self.connection,
            index=False,
            if_exists='append'
        )

    def assign_account(self, customer_id, account_type):
        """
        assign a single account for a customer
        """
        account = Account(customer_id=int(customer_id), account_type=account_type)
        self.session.add(account)
        self.session.commit()
        return account.account_id

    def make_transaction(self, debit_account, credit_account, transaction_date, transaction_amount):
        """
        make a single transaction
        """
        transaction = Transaction(
            debit_account=int(debit_account),
            credit_account=int(credit_account),
            transaction_date=transaction_date,
            transaction_amount=transaction_amount
        )
        self.session.add(transaction)
        self.session.commit()
        return transaction.transaction_id

    def make_transactions(self, data: pd.DataFrame):
        """
        accepts a DataFrame to make multiple transactions
        """
        data['debit_account'] = data['debit_account'].astype(int)
        data['credit_account'] = data['credit_account'].astype(int)
        data.to_sql(
            'transaction',
            self.connection,
            index=False,
            if_exists='append'
        )

