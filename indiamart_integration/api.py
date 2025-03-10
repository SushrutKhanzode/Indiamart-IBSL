from __future__ import unicode_literals
import frappe
from frappe.utils import today
from frappe import _
import json
import requests

@frappe.whitelist()
def add_source_lead():
	lead_sources = ['Indiamart - Call', 'Indiamart - Buy Lead','Indiamart - Direct' ]
	for type in lead_sources:
		if not frappe.db.exists(type):
			doc=frappe.get_doc(dict(
				doctype = "Lead Source",
				source_name = type
			)).insert(ignore_permissions=True)
		if doc:
			frappe.msgprint(_("Lead Source Added For " + type))
		else:
			frappe.msgprint(_(type + " Lead Source Already Available"))

@frappe.whitelist()
def sync_india_mart_lead(from_cron, from_date = None, to_date = None):
	try:
		india_mart_setting = frappe.get_doc("IndiaMart Settings","IndiaMart Setting")
		if (not india_mart_setting.url
			or not india_mart_setting.key):
				frappe.throw(
					msg=_('URL, Key mandatory for Indiamart API Call. Please set them and try again.'),
					title=_('Missing Setting Fields')
				)

		if from_cron == 1:
			req = get_request_url_cron(india_mart_setting)
		else:
			req = get_request_url(india_mart_setting)
		
		res = requests.get(url=req)
		
		if res.text:
			count = 0
			_data = json.loads(res.text)
			if not _data['STATUS'] == 'SUCCESS':
				frappe.throw(_data['MESSAGE'])
			else:
				for row in _data['RESPONSE']:
					doc = add_lead(row)
					if doc:
						count += 1
			if not count == 0:
				frappe.msgprint(_("{0} Lead Created").format(count))

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), _("India Mart Sync Error"))

def get_request_url(india_mart_setting):
	req = str(india_mart_setting.url)+"?glusr_crm_key="+str(india_mart_setting.key)+'&start_time='+str(india_mart_setting.from_date)+'&end_time='+str(india_mart_setting.to_date)
	return req

def get_request_url_cron(india_mart_setting):
	req = str(india_mart_setting.url)+"?glusr_crm_key="+str(india_mart_setting.key)
	return req

@frappe.whitelist()
def cron_sync_lead():
	india_mart_setting = frappe.get_doc("IndiaMart Setting","IndiaMart Setting")
	if not india_mart_setting.enabled:
		return
	try:
		sync_india_mart_lead(from_cron = 1)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), _("India Mart Sync Error"))

@frappe.whitelist()
def add_lead(lead_data):
	qtype_map = {'P' : 'Indiamart - Call', 'B' : 'Indiamart - Buy Lead', 'W' : 'Indiamart - Direct'}
	try:
		if not (frappe.db.exists("Lead",{"india_mart_id":lead_data["UNIQUE_QUERY_ID"]}) or frappe.db.exists("Lead",{"email_id":lead_data["SENDER_EMAIL"]})):
			lead_data = dict(lead_data)
			title,lead_name,email_id,mobile_no,company_name,address_line1,city,state,note,phone = [lead_data.get('SENDER_COMPANY') if lead_data.get('SENDER_COMPANY') else lead_data.get('SENDER_NAME'),lead_data.get("SENDER_NAME"),lead_data.get("SENDER_EMAIL"),lead_data.get("SENDER_MOBILE")[-10:],lead_data.get('SENDER_COMPANY'),lead_data.get('SENDER_ADDRESS'),lead_data.get('SENDER_CITY'),lead_data.get('SENDER_STATE'),lead_data.get('QUERY_MESSAGE') + "\n" + lead_data.get('QUERY_PRODUCT_NAME') + "\n" + lead_data.get('CALL_DURATION') + "\n" + lead_data.get('RECEIVER_MOBILE') + "\n" + lead_data.get('SENDER_EMAIL_ALT') + "\n" + lead_data.get('UNIQUE_QUERY_ID'),lead_data.get('SENDER_MOBILE_ALT')[-10:]]
			doc = frappe.get_doc({
				'doctype' : "Lead",
				'title' : title,
				'lead_name' : lead_name,
				'first_name' : lead_name.split(" ")[0] if " " in lead_name else "",
				'last_name' : lead_name.split(" ")[1] if " " in lead_name else "",
				'email_id' : email_id,
				'mobile_no' : mobile_no,
				'company_name' : company_name, #ok
				'address_line1' : address_line1, #ok
				'city' : city, #ok
				'state' : state, #ok
				'notes' : [
					{
						'note' : note,
					}
					],
				'phone' : phone,
				'status' : 'Lead',
				'source' : qtype_map[lead_data.get("QUERY_TYPE")],
				'india_mart_id':lead_data.get("UNIQUE_QUERY_ID")
			}).insert(ignore_permissions = True)
			return doc
	except Exception as e:
		frappe.log_error(frappe.get_traceback())

