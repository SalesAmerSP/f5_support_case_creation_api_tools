#!/usr/bin/env python3
"""Interactive CLI tool to generate a validated JSON case inputs file for MyF5.

Fetches dynamic metadata (products, versions, severities, timezones) from MyF5
to ensure user inputs are schema-compliant before submitting a case.

Usage:
    python3 examples/myf5_create_inputs_file.py --client-id <id> --client-secret <secret> \
        --output-file case_inputs.json [--auth-fqdn idp.identity.f5.com]
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
try:
    from qkviewmgr import f5functions
except ImportError:
    import f5functions


def main():
    """Gather case attributes interactively and write to JSON output file."""
    args = f5functions.myf5_args(
        (["--output-file"], {"type": str, "help": "Path to write case inputs JSON file", "required": True}),
    )
    access_token = f5functions.myf5_authenticate(
        args.app_id, args.client_id, args.client_secret,
        scope='myf5_scope', auth_url=args.auth_url, auth_fqdn=args.auth_fqdn
    )

    # Use the case-creation-metadata schema to create a case
    print('Gathering case metadata from the support API...')
    case_metadata = f5functions.myf5_retrieve_case_creation_metadata(
        access_token, api_fqdn=args.api_url, k_value=args.k_value
    )
    if case_metadata.status_code != 200:
        raise SystemExit(f'Failed to retrieve case metadata.\nStatus code: {case_metadata.status_code} Full response: {case_metadata.text}')
    case_metadata = case_metadata.json()

    # Test that we can open the output file
    try:
        with open(args.output_file, 'w') as f:
            pass
    except OSError:
        raise SystemExit(f'Failed to open output file {args.output_file}')

    # Gather inputs interactively
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
            print(f'You selected: {inputs["product"]}')

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
            print(f'You selected: {inputs["productVersion"]}')

    # Gather the subject
    print('Please enter the subject of the case:')
    inputs['subject'] = input()
    print(f'Selected Subject: {inputs["subject"]}')

    # Gather the description
    print('Please enter the description of the case:')
    inputs['description'] = input()
    print(f'Selected Description: {inputs["description"]}')

    # Gather the serial number
    print('Please enter the serial number:')
    inputs['serialNumber'] = input()
    print(f'Selected Serial Number: {inputs["serialNumber"]}')

    # Gather the hostname(s)
    print('Please enter the hostname(s):')
    inputs['hostName'] = input()
    print(f'Selected Hostname(s): {inputs["hostName"]}')

    # Gather the priority
    values = case_metadata['data']['priorities']
    for idx, val in enumerate(values):
        print(f'{idx}: {val}')
    choice = ""
    while not (choice.isdigit() and 0 <= int(choice) < len(values)):
        choice = input('Please select a value: ')
    inputs['priority'] = values[int(choice)]
    print(f'Selected Priority: {inputs["priority"]}')

    # Gather the Reason for Contact
    values = case_metadata['data']['reasonsForContact']
    for idx, val in enumerate(values):
        print(f'{idx}: {val}')
    choice = ""
    while not (choice.isdigit() and 0 <= int(choice) < len(values)):
        choice = input('Please select a value: ')
    inputs['reasonForContact'] = values[int(choice)]
    print(f'Selected Reason for Contact: {inputs["reasonForContact"]}')

    # Collect the preferred contact method
    values = case_metadata['data']['preferredContactMethods']
    for idx, val in enumerate(values):
        print(f'{idx}: {val}')
    choice = ""
    while not (choice.isdigit() and 0 <= int(choice) < len(values)):
        choice = input('Please select a value: ')
    inputs['preferredContactMethod'] = values[int(choice)]
    print(f'Selected Preferred Contact Method: {inputs["preferredContactMethod"]}')

    # Collect the cloud provider, if any
    values = case_metadata['data']['cloudProviders']
    for idx, val in enumerate(values):
        print(f'{idx}: {val}')
    choice = ""
    while not (choice.isdigit() and 0 <= int(choice) < len(values)):
        choice = input('Please select a value: ')
    inputs['cloudProvider'] = values[int(choice)]
    print(f'Selected Cloud Provider: {inputs["cloudProvider"]}')

    # Gather the timezone
    values = case_metadata['data']['timeZones']
    for idx, val in enumerate(values):
        print(f'{idx}: {val}')
    choice = ""
    while not (choice.isdigit() and 0 <= int(choice) < len(values)):
        choice = input('Please select a value: ')
    inputs['timeZone'] = values[int(choice)]
    print(f'Selected TimeZone: {inputs["timeZone"]}')

    # Customer ticket number (optional)
    customer_ticket = input('Do you have a customer ticket number? (y/n): ')
    if customer_ticket.lower() in ('y', 'yes'):
        inputs['customerTicketNumber'] = input()
        print(f'Customer Ticket Number: {inputs["customerTicketNumber"]}')

    # Gather the Case Owner Email Address
    case_owner_email = input('Do you want to override the default case owner email address? (y/n): ')
    if case_owner_email.lower() in ('y', 'yes'):
        print('OPTIONAL: specify contact email address')
        inputs['caseOwnerEmail'] = input()
        print(f'Case Owner Email: {inputs["caseOwnerEmail"]}')

    # Add alternative contact info (optional)
    print('OPTIONAL: specify an alternate contact email address')
    alternate_contact = input('Do you want to add an alternate contact? (y/n): ')
    if alternate_contact.lower() in ('y', 'yes'):
        inputs['alternateContact'] = {
            'firstName': input('Please enter the first name of the alternate contact: '),
            'lastName': input('Please enter the last name of the alternate contact: '),
            'email': input('Please enter the email address of the alternate contact: '),
            'phoneNumber': input('Please enter the phone number of the alternate contact: '),
        }

    # Save the inputs to the output file in JSON format
    try:
        with open(args.output_file, 'w') as f:
            json.dump(inputs, f, indent=2)
        print(f'Inputs successfully saved to {args.output_file}')
    except OSError as e:
        raise SystemExit(e)


if __name__ == "__main__":
    main()
