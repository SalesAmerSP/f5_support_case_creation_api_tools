#!/usr/bin/env python

import f5functions
import argparse
import json

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client-id', type=str, help='Support API Key', required=True)
    parser.add_argument('--client-secret', type=str, help='Support API Secret', required=True)
    parser.add_argument('--output-file', type=str, help='Input file', required=True)
    parser.add_argument('--app-id', type=str, help='Advanced Users Only - overwrite Support App ID', required=False, default='aus19gt5bu0jGw9Fi358')
    parser.add_argument('--api-url', type=str, help='Advanced Users Only - Support API URL', required=False, default="https://support.f5.com")
    parser.add_argument('--k-value', type=str, help='Advanced Users Only - overwrite required API k value', required=False, default="UKKD3Vxv7NHrM3QmYk8Fk2mZnLtljAKX") 
    return parser.parse_args()

def main():
    # Generate access token
    api_token_auth_response = f5functions.myf5_retrieve_access_token(parse_args().app_id, parse_args().client_id, parse_args().client_secret)
    if api_token_auth_response.status_code != 200:
        raise SystemExit(f'Failed to retrieve API Token.\nStatus code: {api_token_auth_response.status_code} Full response: {api_token_auth_response.text}')
    else:
        print(f'Authentication successful.')

    # Use the case-creation-metadata schema to create a case
    print('Gathering case metadata from the support API')
    case_metadata = f5functions.myf5_retrieve_case_creation_metadata(api_token_auth_response.json()["access_token"])
    if case_metadata.status_code != 200:
        raise SystemExit(f'Failed to retrieve case metadata.\nStatus code: {case_metadata.status_code} Full response: {case_metadata.text}')
    else:
        case_metadata = case_metadata.json()

    # Test that we can open the output file
    try:
        with open(parse_args().output_file, 'w') as f:
            f.close()
    except:
        raise SystemExit(f'Failed to open output file {parse_args().output_file}')

    # The the keys and values in the case-creation-metadata.json file and prompt the user for values
    # We'll set static values here as well
    inputs = {}
    inputs['status'] = 'New'

    # Gather the Product Family
    print('Select a product family')
    productFamilies = case_metadata['data']['prodFamilies']
    for current_family in productFamilies:
        print(f'{productFamilies.index(current_family)}: {current_family["name"]}')
    choice = ""
    while not (choice.isdigit() and 0 <= int(choice) < len(productFamilies)):
        choice = input('Please select a value: ')
    inputs['productFamily'] = productFamilies[int(choice)]['name']
    print(f'You selected: {productFamilies[int(choice)]["name"]}')

    # Filter the product family and select a product
    productFamily = next((item for item in productFamilies if item['name'] == inputs['productFamily']), None)
    for (key, value) in productFamily.items():
        if key == 'products':
            for idx, val in enumerate(value):
                print(f'{idx}: {val["name"]}')
            choice = ""
            while not (choice.isdigit() and 0 <= int(choice) < len(value)):
                choice = input('Please select a value: ')
            inputs['product'] = value[int(choice)]['name']
            print(f'You selected: {inputs['product']}')

    # Select a version from the product
    product = next((item for item in productFamily['products'] if item['name'] == inputs['product']), None)
    for (key, value) in product.items():
        if key == 'versions':
            for idx, val in enumerate(value):
                print(f'{idx}: {val}')
            choice = ""
            while not (choice.isdigit() and 0 <= int(choice) < len(value)):
                choice = input('Please select a value: ')
            inputs['productVersion'] = value[int(choice)]
            print(f'You selected: {inputs['productVersion']}')
            
    # Gather the subject
    print(f'Please enter the subject of the case:')
    inputs['subject'] = input()
    # Print the selected subject
    print(f'Selected Subject: {inputs["subject"]}')

    # Gather the description
    print(f'Please enter the description of the case:')
    inputs['description'] = input()
    # Print the selected description
    print(f'Selected Description: {inputs["description"]}')

    # Gather the serial number
    print(f'Please enter the serial number:')
    inputs['serialNumber'] = input()
    # Print the selected serial number
    print(f'Selected Serial Number: {inputs["serialNumber"]}')

    # Gather the hostname(s)
    print(f'Please enter the hostname(s):')
    inputs['hostName'] = input()
    # Print the selected hostname(s)
    print(f'Selected Hostname(s): {inputs["hostName"]}')   
    
    # Gather the priority 
    values = case_metadata['data']['priorities']
    for idx, val in enumerate(values):
        print(f'{idx}: {val}')
    choice = ""
    while not (choice.isdigit() and 0 <= int(choice) < len(values)):
        choice = input('Please select a value: ')
    inputs['priority'] = values[int(choice)]
    # Print the selected priority
    print(f'Selected Priority: {inputs["priority"]}')

    # Gather the Reason for Contact
    values = case_metadata['data']['reasonsForContact']
    for idx, val in enumerate(values):    
        print(f'{idx}: {val}')
    choice = ""
    while not (choice.isdigit() and 0 <= int(choice) < len(values)):
        choice = input('Please select a value: ')
    inputs['reasonForContact'] = values[int(choice)]
    # Print the selected reason for contact
    print(f'Selected Reason for Contact: {inputs["reasonForContact"]}')

    # Collect the preferred contact method
    values = case_metadata['data']['preferredContactMethods']
    for idx, val in enumerate(values):
        print(f'{idx}: {val}')
    choice = ""
    while not (choice.isdigit() and 0 <= int(choice) < len(values)):
        choice = input('Please select a value: ')
    inputs['preferredContactMethod'] = values[int(choice)]
    # Print the selected preferred contact method
    print(f'Selected Preferred Contact Method: {inputs["preferredContactMethod"]}')

    # Collect the cloud provider, if any
    values = case_metadata['data']['cloudProviders']
    for idx, val in enumerate(values):
        print(f'{idx}: {val}')
    choice = ""
    while not (choice.isdigit() and 0 <= int(choice) < len(values)):
        choice = input('Please select a value: ')
    inputs['cloudProvider'] = values[int(choice)]
    # Print the selected cloud provider
    print(f'Selected Cloud Provider: {inputs["cloudProvider"]}')

    # Gather the timezone
    values = case_metadata['data']['timeZones']
    for idx, val in enumerate(values):
        print(f'{idx}: {val}')
    choice = ""
    while not (choice.isdigit() and 0 <= int(choice) < len(values)):
        choice = input('Please select a value: ')
    inputs['timeZone'] = values[int(choice)]
    # Print the selected timezone
    print(f'Selected TimeZone: {inputs["timeZone"]}')

    # Customer ticket number (optional)
    customer_ticket = input(f'Do you have a customer ticket number? (y/n): ')
    if customer_ticket == 'y' or customer_ticket == 'Y' or customer_ticket == 'yes' or customer_ticket == 'Yes':
        inputs['customerTicketNumber'] = input()
        # Print the selected customer ticket number
        print(f'Customer Ticket Number: {inputs["customerTicketNumber"]}')

    # Gather the Case Owner Email Address
    case_owner_email =input(f'Do you want to override the default case owner email address? (y/n): ')
    if case_owner_email == 'y' or case_owner_email == 'Y' or case_owner_email == 'yes' or case_owner_email == 'Yes':
        print(f'OPTIONAL: specify contact email address')
        inputs['caseOwnerEmail'] = input()
        # Print the entered address if specified
        print(f'Case Owner Email: {inputs["caseOwnerEmail"]}')
    
    # Add alternative contact info (optional)
    print(f'OPTIONAL: specify an alternate contact email address')
    alternate_contact = input(f'Do you want to add an alternate contact? (y/n): ')
    if alternate_contact == 'y' or alternate_contact == 'Y' or alternate_contact == 'yes' or alternate_contact == 'Yes':
        inputs['alternateContact'] = {}
        inputs['alternateContact']['firstName'] = input('Please enter the first name of the alternate contact: ')
        inputs['alternateContact']['lastName'] = input('Please enter the last name of the alternate contact: ')
        inputs['alternateContact']['email'] = input('Please enter the email address of the alternate contact: ')
        inputs['alternateContact']['phoneNumber'] = input('Please enter the phone number of the alternate contact: ')

    # # Gather the subscription ID
    # values = case_metadata['data']['subscriptions']
    # for idx, val in enumerate(values):
    #     print(f'{idx}: {val}')
    # choice = ""
    # while not (choice.isdigit() and 0 <= int(choice) < len(values)):
    #     choice = input('Please select a value: ')
    #     inputs['subscriptionId'] = values[int(choice)]
    # # Print the selected subscription ID
    # print(f'Selected Subscription ID: {inputs["subscriptionId"]}')  

    # # Gather the NGINX Plus Version
    # values = case_metadata['data']['nginxPlusVersions']
    # for idx, val in enumerate(values):
    #     print(f'{idx}: {val}')
    # choice = ""
    # while not (choice.isdigit() and 0 <= int(choice) < len(values)):
    #     choice = input('Please select a value: ')
    # inputs['nginxPlusVersion'] = values[int(choice)]
    # # Print the selected NGINX Plus Version
    # print(f'Selected NGINX Plus Version: {inputs["nginxPlusVersion"]}')
    
    # # Gather the Linux Distribution
    # values = case_metadata['data']['linuxDistributions']        
    # for idx, val in enumerate(values):
    #     print(f'{idx}: {val}')
    # choice = ""
    # while not (choice.isdigit() and 0 <= int(choice) < len(values)):
    #     choice = input('Please select a value: ')
    # inputs['linuxDistribution'] = values[int(choice)]
    # # Print the selected Linux Distribution
    # print(f'Selected Linux Distribution: {inputs["linuxDistribution"]}')    
    
    # Save the inputs to the output file in JSON format
    try:
        with open(parse_args().output_file, 'w') as f:
            f.write(json.dumps(inputs))
            f.close()
        print(f'Inputs saved to {parse_args().output_file}')
    except IOError as e:
        raise SystemExit(e)
    except Exception as e:
        raise SystemExit(e)
    
if __name__ == "__main__":
    main()
    