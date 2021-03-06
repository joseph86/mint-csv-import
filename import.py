"""
#################################
Pre-requisites needed
#################################

If you are missing any of the following you can install with:

	pip install $name
	Example: pip install csv 

OR if you are using pip3

	pip3 install $name 
	Example: pip3 install csv

On Windows 10 use

	py -m pip install $name
"""

import csv
import datetime
import os
import random
import time
import urllib.parse
import pycurl
import certifi
from io import BytesIO


"""
#################################
Overview: 
#################################

Simulates bulk manual transaction adds to mint.com. Mint manual transactions are submitted as "cash transactions" which 
will mean it shows in your cash / all accounts transaction list. You cannot submit manual transactions against credit 
cards or other integrated bank accounts (even in Mint's UI this is not possible and ends up as cash transction). 

Approach Credits: 
Simulating manual transactions from UI is based on Nate H's proof of concept from https://www.youtube.com/watch?v=8AJ3g5JGmdU

Python Credits:
Credit to https://github.com/nathanielkam/ who provided the basis for this script
Credit to https://github.com/ukjimbow for his work on Mint imports for UK users in https://github.com/ukjimbow/mint-transactions

Process Documentation: 
1. Import CSV
2. Process date for correct format 
3. Process merchant to remove excess whitespace
4. Process categories change your banks category name into a mint category ID (limited in scope based on the categories
I needed when I wrote this)
5. Process amount for positive or negative value indicating income or expense 
6. Send POST Request to mint as new transaction. 
7. Force Randomized Wait Time before starting next request

Future Development:
1. Grab the cookie from the browser
2. Get the account, tags, referrer, and token from the browser
3. Fiddle with the mtType and cashTxnType and see if I can associate it with one of the existing credit card accounts

"""

"""
#################################
Settings 
#################################
"""
csv_name = 'Import.csv' # name of csv you you want import to mint [string.csv]
verbose_output = 1 # should verbose messages be printed [0,1] 
uk_to_us = 0 # do you need to change dates from UK to US format [0,1]
min_wait = 0 # min wait time in seconds between requests, int[0-n]
max_wait = 2 # max wait time in seconds between requests, int[0-n]

"""
#################################
Mint Client Credentials 
#################################

You will need the tags, cookie, and token to simulate a UI form submission. You can get these by opening developer tools > network analysis tab and doing 
a test submission in mint.com. From there look for the post request to "updateTransaction.xevent" and grab the credentials from the header and body
"""
account = '' # grab from POST request form body in devtools
tag1 = '' # in form of tagXXXXXXX
tag2 = '' # in form of tagXXXXXXX
tag3 = '' # in form of tagXXXXXXX
cookie = ''
# grab from POST request header in devtools 
referrer = 'https://mint.intuit.com/transaction.event'
# grab from POST request header in devtools 
token = ''
# grab from POST request form body in devtools 

"""
#################################
Set Up Debug Function
#################################
"""
def test(debug_type, debug_msg):
    if debug_type < 5:
	print("debug(" + str(debug_type) + "): " + debug_msg.decode('iso-8859-1'))


"""
#################################
Import CSV using the pythons csv reader 
#################################
"""
csv_object = csv.reader(open(csv_name, newline=''))
next(csv_object)

for row in csv_object:

	# Initialize Variables
	date = (row[0]) 
	postDate = (row[1])
	merchant = (row[2])
	catID = (row[3])
	typeID = (row[4])
	amount = (float(row[5]))
	expense = 'true'
	curl_input = 'Error: Did not Generate'
	curl_output = 'Error: Did not run' 

	"""
	#################################
	Process Date for format 
	#################################
	"""

	# Convert Commonwealth to US Date System 
	if uk_to_us == 1: # based on setting
		dateconv = time.strptime(date,"%d/%m/%Y") # not needed for US to US
		date = (time.strftime("%m/%d/%Y",dateconv)) # converted new US date format from UK

	"""
	#################################
	Process Merchant to remove extra whitespace. American Express loves adding extra whitespace
	#################################
	"""
	separator = ' '
	merchant = separator.join(merchant.split())

	"""
	#################################
	Process Categories 
	#################################
	"""
	# Category ID Mapping Function 
	def category_id_switch(import_category):

		# Define mapping of import categories to : Mint Category IDs
		switcher={
			#Chase Categories
			'Gas':1401,
			'Food & Drink':7,
			'Groceries':701,
			'Bills & Utilities':13,
			'Shopping':2,
			'Health & Wellness':5,
			'Personal':4,
			'Payment':2101,
			'Travel':15,
			'Entertainment':1,
			'Automotive':14,
			'Education':10,
			'Professional Services':17,
			'Home':12,
			'Fees & Adjustments':16,
			'Gifts & Donations':8,
			#American Express Categories
			'Merchandise & Supplies-Groceries':701,
			'Transportation-Fuel':1401,
			'Fees & Adjustments-Fees & Adjustments':16,
			'Merchandise & Supplies-Wholesale Stores':2,
			'Restaurant-Restaurant':707,
			'Payment':2101,
			#the following categories are mint categories. I added my own categories to transactions downloaded from Citi
			# because Citi does not included categories in downloaded transactions
			# Some categories are repeated because both Mint uses the same name as another bank
			'Auto & Transport':14,
			'Auto Insurance':1405,
			'Auto Payment':1404,
			'Gas & Fuel':1401,
			'Parking':1402,
			'Public Transportation':1406,
			'Service & Parts':1403,
			'Bills & Utilities':13,
			'Home Phone':1302,
			'Internet':1303,
			'Mobile Phone':1304,
			'Television':1301,
			'Utilities':1306,
			'Business Services':17,
			'Advertising':1701,
			'Legal':1705,
			'Office Supplies':1702,
			'Printing':1703,
			'Shipping':1704,
			'Education':10,
			'Books & Supplies':1003,
			'Student Loan':1002,
			'Tuition':1001,
			'Entertainment':1,
			'Amusement':102,
			'Arts':101,
			'Movies & DVDs':104,
			'Music':103,
			'Newspapers & Magazines':105,
			'Fees & Charges':16,
			'ATM Fee':1605,
			'Bank Fee':1606,
			'Finance Charge':1604,
			'Late Fee':1602,
			'Service Fee':1601,
			'Trade Commissions':1607,
			'Financial':11,
			'Financial Advisor':1105,
			'Life Insurance':1102,
			'Food & Dining':7,
			'Alcohol & Bars':708,
			'Coffee Shops':704,
			'Fast Food':706,
			'Groceries':701,
			'Restaurants':707,
			'Gifts & Donations':8,
			'Charity':802,
			'Gift':801,
			'Health & Fitness':5,
			'Dentist':501,
			'Doctor':502,
			'Eyecare':503,
			'Gym':507,
			'Health Insurance':506,
			'Pharmacy':505,
			'Sports':508,
			'Home':12,
			'Furnishings':1201,
			'Home Improvement':1203,
			'Home Insurance':1206,
			'Home Services':1204,
			'Home Supplies':1208,
			'Lawn & Garden':1202,
			'Mortgage & Rent':1207,
			'Income':30,
			'Bonus':3004,
			'Interest Income':3005,
			'Paycheck':3001,
			'Reimbursement':3006,
			'Rental Income':3007,
			'Returned Purchase':3003,
			'Kids':6,
			'Allowance':610,
			'Baby Supplies':611,
			'Babysitter & Daycare':602,
			'Child Support':603,
			'Kids Activities':609,
			'Toys':606,
			'Misc Expenses':70,
			'Personal Care':4,
			'Hair':403,
			'Laundry':406,
			'Spa & Massage':404,
			'Pets':9,
			'Pet Food & Supplies':901,
			'Pet Grooming':902,
			'Veterinary':903,
			'Shopping':2,
			'Books':202,
			'Clothing':201,
			'Electronics & Software':204,
			'Hobbies':206,
			'Sporting Goods':207,
			'Taxes':19,
			'Federal Tax':1901,
			'Local Tax':1903,
			'Property Tax':1905,
			'Sales Tax':1904,
			'State Tax':1902,
			'Transfer':21,
			'Credit Card Payment':2101,
			'Transfer for Cash Spending':2102,
			'Travel':15,
			'Air Travel':1501,
			'Hotel':1502,
			'Rental Car & Taxi':1503,
			'Vacation':1504,
			'Uncategorized':20,
			'Cash & ATM':2001,
			'Check':2002,
			'Hide from Budgets & Trends':40,

		} 
		# Get the mint category ID from the map 
		return switcher.get(import_category,20) # For all other unmapped cases return uncategorized category "20" 

	# Category NAME Mapping Function 
	def category_name_switch(mint_id):

		# Define mapping of import categories to : Mint Category IDs
		switcher={
			14:'Auto & Transport',
			1405:'Auto Insurance',
			1404:'Auto Payment',
			1401:'Gas & Fuel',
			1402:'Parking',
			1406:'Public Transportation',
			1403:'Service & Parts',
			13:'Bills & Utilities',
			1302:'Home Phone',
			1303:'Internet',
			1304:'Mobile Phone',
			1301:'Television',
			1306:'Utilities',
			17:'Business Services',
			1701:'Advertising',
			1705:'Legal',
			1702:'Office Supplies',
			1703:'Printing',
			1704:'Shipping',
			10:'Education',
			1003:'Books & Supplies',
			1002:'Student Loan',
			1001:'Tuition',
			1:'Entertainment',
			102:'Amusement',
			101:'Arts',
			104:'Movies & DVDs',
			103:'Music',
			105:'Newspapers & Magazines',
			16:'Fees & Charges',
			1605:'ATM Fee',
			1606:'Bank Fee',
			1604:'Finance Charge',
			1602:'Late Fee',
			1601:'Service Fee',
			1607:'Trade Commissions',
			11:'Financial',
			1105:'Financial Advisor',
			1102:'Life Insurance',
			7:'Food & Dining',
			708:'Alcohol & Bars',
			704:'Coffee Shops',
			706:'Fast Food',
			701:'Groceries',
			707:'Restaurants',
			8:'Gifts & Donations',
			802:'Charity',
			801:'Gift',
			5:'Health & Fitness',
			501:'Dentist',
			502:'Doctor',
			503:'Eyecare',
			507:'Gym',
			506:'Health Insurance',
			505:'Pharmacy',
			508:'Sports',
			12:'Home',
			1201:'Furnishings',
			1203:'Home Improvement',
			1206:'Home Insurance',
			1204:'Home Services',
			1208:'Home Supplies',
			1202:'Lawn & Garden',
			1207:'Mortgage & Rent',
			30:'Income',
			3004:'Bonus',
			3005:'Interest Income',
			3001:'Paycheck',
			3006:'Reimbursement',
			3007:'Rental Income',
			3003:'Returned Purchase',
			6:'Kids',
			610:'Allowance',
			611:'Baby Supplies',
			602:'Babysitter & Daycare',
			603:'Child Support',
			609:'Kids Activities',
			606:'Toys',
			70:'Misc Expenses',
			4:'Personal Care',
			403:'Hair',
			406:'Laundry',
			404:'Spa & Massage',
			9:'Pets',
			901:'Pet Food & Supplies',
			902:'Pet Grooming',
			903:'Veterinary',
			2:'Shopping',
			202:'Books',
			201:'Clothing',
			204:'Electronics & Software',
			206:'Hobbies',
			207:'Sporting Goods',
			19:'Taxes',
			1901:'Federal Tax',
			1903:'Local Tax',
			1905:'Property Tax',
			1904:'Sales Tax',
			1902:'State Tax',
			21:'Transfer',
			2101:'Credit Card Payment',
			2102:'Transfer for Cash Spending',
			15:'Travel',
			1501:'Air Travel',
			1502:'Hotel',
			1503:'Rental Car & Taxi',
			1504:'Vacation',
			20:'Uncategorized',
			2001:'Cash & ATM',
			2002:'Check',
			40:'Hide from Budgets & Trends',
		} 
		# Get the mint category NAME from the map 
		return switcher.get(mint_id,'Uncategorized') # For all other unmapped cases return uncategorized category "20" 

	# typeID payment overrides all categories 
	if typeID == "Payment":
		catID = '2101' # Since I was importing credit cards I have mine set to credit card payment. If you are doing bank accounts you many want to change this to payment general
	
	# if type is NOT payment then do a category check 
	else:

		# if there IS no cat it is uncategorized 
		if len(catID) == 0: 
			catID = '20' # mint's uncategorized category

		# If there is a category check it against mapping       
		else : 
			# Use a switch since there may be MANY category maps 
			catID = category_id_switch(catID)


	# Set mint category name by looking up name in ID map
	category = category_name_switch(catID)
	#no need for this. I'm encoding all at once
	#category = urllib.parse.quote(category)

	"""
	#################################
	Process Amount seeing if transaction is an expense or income.   
	#################################
	"""
	if amount < 0: 
		expense = 'true' # when amount is less than 0 this is an expense, ie money left your account, ex like buying a sandwich.                                        
	else: 
		expense = 'false' # when amount is greater than 0 this is income, ie money went INTO your account, ex like a paycheck.                          
	amount = str(amount) # convert amount to string so it can be concatenated in POST request 

	"""
	#################################
	Build CURL POST Request
	# I've opted to use PyCurl for the curl command in order to make the code better compatible with other platforms.
	# If I'm honest, I couldn't get it to work with Windows 10 default curl. It kept mangling my cookies and munging my data
	#################################
	"""
	curl = pycurl.Curl()
	curl.setopt(pycurl.POST, 1)
	curl.setopt(curl.URL, 'https://mint.intuit.com/updateTransaction.xevent')
	curl.setopt(curl.USERAGENT, "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0")
	curl.setopt(curl.HTTPHEADER, ["Accept-Encoding: gzip, deflate, br",
				      "Accept-Language: en-US,en;q=0.5",
				      "connection: keep-alive",
				      "Origin: https://mint.intuit.com",
				      "referer: https://mint.intuit.com/transaction.event",
				      "TE: Trailers",                                    
				      "content-type: application/x-www-form-urlencoded; charset=UTF-8",
				      "X-Requested-With: XMLHttpRequest"])
	curl.setopt(curl.COOKIE, cookie)
	buffer = BytesIO()
	curl.setopt(curl.WRITEDATA, buffer)
	curl.setopt(curl.CAINFO, certifi.where()) 

	# Generate form data
	fields = {"cashTxnType":"on","mtCashSplit":"on","mtCheckNo":"", tag1 :"0", tag2 : "0", tag3 : "0",
		   "task":"txnadd","txnId":":0","mtType":"cash","mtAccount": account,
		   "symbol":"","note":"","isInvestment":"false","catId":catID,"category":category,
		   "merchant":merchant,"date":date,"amount":amount,"mtIsExpense":expense,
		   "mtCashSplitPref":"1","token": token}
	curl_data = urllib.parse.urlencode(fields)
	curl_input = curl_data
	curl.setopt(pycurl.POSTFIELDS, curl_data)

	#debugging
	if verbose_output == 1:
		curl.setopt(pycurl.VERBOSE, True)
		#curl.setopt(pycurl.DEBUGFUNCTION, test)
	
	"""
	#################################
	Submit CURL POST Request
	#################################
	"""
	#curl.perform()

	"""
	#################################
	Verbose Output for Debug
	#################################
	"""
	if verbose_output == 1: 
		print ('Transaction Date:', date) # date of transaction
		print ('Merchant', merchant) # merchant Description 
		print ('Category ID:', catID) # category of transaction
		print ('Category Name:', category) # category of transaction
		print ('Amount:', amount) # amount being processed
		print ('Expense:', expense) # in amount expense
		print ('CURL Request:', curl_data)# what was sent to mint
		print('HTTP Code: ', curl.getinfo(curl.HTTP_CODE))
		body = buffer.getvalue()
		print ('CURL Response:', body.decode('iso-8859-1')) # what was returned from mint OR curl ERROR
		print ('\n\n==============\n') # new line break

	"""
	#################################
	Force a random wait between 2 and 5 seconds per requests to simulate UI and avoid rate limiting
	#################################
	"""
	curl.close()
	time.sleep(random.randint(min_wait, max_wait))
