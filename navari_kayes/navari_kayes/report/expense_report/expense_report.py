# Copyright (c) 2023, Navari Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"));
	return get_columns(), get_data(filters);

def get_columns():
	return [
		{
			'fieldname': 'account',
			'label': _('Account'),
			'fieldtype': 'Link',
			'options': 'Account',
			'width': 240
		},
		{
			'fieldname': 'cost_center',
			'label': _('Cost Center'),
			'fieldtype': 'Link',
			'options': 'Cost Center',
			'width': 180
		},
		{
			'fieldname': 'debit',
			'label': _('Debit'),
			'fieldtype': 'Currency',
			'width': 150
		},
		{
			'fieldname': 'credit',
			'label': _('Credit'),
			'fieldtype': 'Currency',
			'width': 140
		},
		{
			'fieldname': 'balance',
			'label': _('Balance'),
			'fieldtype': 'Currency',
			'width': 150
		}
	];

def get_data(filters):
	data = []
	company, from_date, to_date, account = filters.get('company'), filters.get('from_date'), filters.get('to_date'), filters.get('account');

	def is_group(account):
		return frappe.db.get_value('Account', account, 'is_group');

	def get_pending_accounts(accounts_list):
		for account in accounts_list:
			if is_group(account):
				insert_index = accounts_list.index(account) + 1;
				child_accounts = frappe.db.get_all('Account', filters = { 'parent_account': account }, pluck = 'name');
				accounts_list[ insert_index:insert_index ] = child_accounts;

		return accounts_list;

	root_account = '5000 - Expenses - KTE' if not account else account;
	pending_accounts = get_pending_accounts([root_account]);

	conditions = " AND gle.docstatus = 1 ";

	if company:
		conditions += f" AND gle.company = '{company}'";

	def append_accounts(account, indent, conditions, from_date, to_date):
		conditions += f" AND gle.account LIKE '%{account}'";

		if is_group(account):
			parent = frappe.db.get_value('Account', account, 'parent_account');
			data.append({ 'account': account, 'indent': indent, 'parent': parent });
		else:	
			gl_entry = frappe.db.sql(f"""
				SELECT  SUM(gle.credit_in_account_currency) as "credit",
						gle.account as "account",
						SUM(gle.debit_in_account_currency) as "debit",
						SUM(gle.debit_in_account_currency - gle.credit_in_account_currency) as "balance",
						gle.cost_center as "cost_center",
						ac.parent_account as "parent"
				FROM `tabGL Entry` as gle
				INNER JOIN `tabAccount` as ac
				ON gle.account = ac.name
				WHERE (gle.creation BETWEEN '{from_date}' AND '{to_date}') {conditions}
				""", as_dict = True);

			gl_entry = gl_entry[0];
			gl_entry['indent'] = indent;

			totals_account = gl_entry['parent'];
			data.append(gl_entry);

			# while totals_account:
			# 	for x in data:
			# 		if x['account'] == totals_account['parent']:
			# 			x['debit'] = x['debit'] + totals_account['debit'] if x.get('debit') else totals_account['debit'];
			# 			x['credit'] = x['credit'] + totals_account['credit'] if x.get('credit') else totals_account['credit'];
			# 			x['balance'] = x['balance'] + totals_account['balance'] if x.get('balance') else totals_account['balance'];

			# 			totals_account = x['parent'];


	for account in pending_accounts:
		parent_account = frappe.db.get_value('Account', account, 'parent_account');

		parent_row = list(filter(lambda x: x['account'] == parent_account, data));

		indent = (parent_row[0]['indent']) + 1 if parent_row else 0;

		append_accounts(account, indent, conditions, from_date, to_date);

	# data = list(filter(lambda x: x['balance'], data));	

	return data;

	