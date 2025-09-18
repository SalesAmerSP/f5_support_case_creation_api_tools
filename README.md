# myf5_proactive_case_generation
Generates a proactive support case using MyF5 and iHealth; includes qkview generation, retrieval and upload to iHealth.

## Index
- [myf5\_proactive\_case\_generation](#myf5_proactive_case_generation)
  - [Index](#index)
  - [Support](#support)
  - [Toolset](#toolset)
    - [BIG-IP Tools](#big-ip-tools)
    - [iHealth Tools](#ihealth-tools)
    - [MyF5.com Tools](#myf5com-tools)
  - [Pre-requisites](#pre-requisites)
  - [Usage](#usage)

## Support

This is not an official F5 tool. Support for this tool is not provided by F5, Inc. Usage is at your own risk. Please report any issues to [github](https://github.com/f5devcentral/myf5_proactive_case_generation/issues). The MyF5 API, iHealth API and iControl REST API is subject to change at any time. This tool set was developed and tested using TMOS 17.5.0. 

## Toolset

This is a collection of tools that can be used to generate a proactive support case using MyF5 and iHealth. It's important to review the [pre-requisites](#pre-requisites) before using these tools.

### BIG-IP Tools

- bigip_connectivity_test.py

    This tool is used to verify connectivity to a BIG-IP. It's not used by the other tools.

    Required arguments:

    - ``--host``: The hostname of the BIG-IP.
    - ``--username``: The username for the BIG-IP.
    - ``--password``: The password for the BIG-IP.

- bigip_generate_qkview.py

    This tool is used to generate a QKView on a BIG-IP. Qkviews are saved on the BIG-IP in this folder: ```/shared/tmp/qkviews```.

    Required arguments:

    - ``--host``: The hostname of the BIG-IP.
    - ``--username``: The username for the BIG-IP.
    - ``--password``: The password for the BIG-IP.
   
    Optional arguments: 

    - ``--filename``: The name of the QKView to generate. If not provided, the randomly created task id is used.
    - ``--skip-wait``: Skip the wait for QKView to complete.
    - ``--wait-interval``: Wait interval in seconds.
    - 

- bigip_list_qkviews.py

    This tool is used to list QKViews on a BIG-IP.

    Required arguments:

    - ``--host``: The hostname of the BIG-IP.
    - ``--username``: The username for the BIG-IP.
    - ``--password``: The password for the BIG-IP.

- bigip_download_qkview.py

    Required arguments:

    - ``--host``: The hostname of the BIG-IP.
    - ``--username``: The username for the BIG-IP.
    - ``--password``: The password for the BIG-IP.
    - ``--filename``: The name of the QKView to download.

- bigip_delete_qkview.py

    Required arguments:

    - ``--host``: The hostname of the BIG-IP.
    - ``--username``: The username for the BIG-IP.
    - ``--password``: The password for the BIG-IP.
    - ``--filename``: The id of the QKView to delete.

### iHealth Tools

- ihealth_connectivity_test.py

    This tool is used to verify connectivity to iHealth. It's not used by the other tools.

    Required arguments:

    - ``--client-id``: The Support API Key.
    - ``--client-secret``: The Support API Secret.

    Optional arguments:

    - ``--app-id``: The Advanced Users Only - Support App ID. Do not use unless instructed by the F5 account team.

- ihealth_list_qkviews.py

    This tool is used to list QKViews on iHealth.

    Required arguments:

    - ``--client-id``: The Support API Key.
    - ``--client-secret``: The Support API Secret.

    Optional arguments:

    - ``--app-id``: The Advanced Users Only - Support App ID. Do not use unless instructed by the F5 account team.

- ihealth_upload_qkview.py

    This tool is used to upload a QKView to iHealth.

    Required arguments:

    - ``--client-id``: The Support API Key.
    - ``--client-secret``: The Support API Secret.
    - ``--filename``: The name of the QKView to upload.

    Optional arguments:

    - ``--support-case``: Existing support case number to which to attach the QKView.
    - ``--app-id``: The Advanced Users Only - Support App ID. Do not use unless instructed by the F5 account team.

### MyF5.com Tools

- myf5_connectivity_test.py

    This tool is used to verify connectivity to MyF5.com. It's not used by the other tools.

    Required arguments:

    - ``--client-id``: The Support API Key.
    - ``--client-secret``: The Support API Secret.

    Optional arguments:

    - ``--app-id``: The Advanced Users Only - overwrite Support App ID.

- myf5_create_inputs_file.py
  
    This tool is used to create the inputs file for creating a support case on MyF5.com. It downloads the case creation metadata (list of valid answers) from MyF5.com and uses that to create the inputs file. The inputs file is used by myf5_create_new_support_case.py. 

    Required arguments:

    - ``--client-id``: The Support API Key.
    - ``--client-secret``: The Support API Secret.
    - ``--output-file``: The name of the output file.

    Optional arguments:

    - ``--app-id``: The Advanced Users Only - overwrite Support App ID.
    - ``--api-url``: The Advanced Users Only - overwrite Support API URL.
    - ``--k-value``: The Advanced Users Only - overwrite required API k value.

- myf5_create_new_support_case.py

    This tool is used to create a new support case on MyF5.com.

    Required arguments:

    - ``--client-id``: The Support API Key.
    - ``--client-secret``: The Support API Secret.
    - ``--inputs-file``: The name of the inputs file.

    Optional arguments:

    - ``--app-id``: The Advanced Users Only - overwrite Support App ID.
    - ``--api-url``: The Advanced Users Only - overwrite Support API URL.
    - ``--k-value``: The Advanced Users Only - overwrite required API k value.

- myf5_add_comments_to_existing_case.py

    This tool is used to add comments to an existing support case on MyF5.com.

    Required arguments:

    - ``--client-id``: The Support API Key.
    - ``--client-secret``: The Support API Secret.
    - ``--case-number``: The F5 Support Case Number.
    - ``--comment-text-file``: The name of the file containing notes to attach.

    Optional arguments:

    - ``--app-id``: The Advanced Users Only - overwrite Support App ID.
    - ``--api-url``: The Advanced Users Only - overwrite Support API URL.
    - ``--k-value``: The Advanced Users Only - overwrite required API k value.

- myf5_list_existing_cases.py

    This tool is used to list existing support cases on MyF5.com.
    
    Required arguments:

    - ``--client-id``: The Support API Key.
    - ``--client-secret``: The Support API Secret.

    Optional arguments:

    - ``--show-closed``: Show closed cases.
    - ``--app-id``: The Advanced Users Only - overwrite Support App ID.
    - ``--api-url``: The Advanced Users Only - overwrite Support API URL.
    - ``--k-value``: The Advanced Users Only - overwrite required API k value.
  
- myf5_retrieve_case_creation_metadata.py

    This tool is used to retrieve the metadata for creating a support case on MyF5.com. This is not a necessary step for the other tools. Note that the metadata can be written to a file or printed to stdout; failure to provide one of these options will result in the metadata not being displayed or saved to disk.

    Required arguments:

    - ``--client-id``: The Support API Key.
    - ``--client-secret``: The Support API Secret.

    Optional arguments:

    - ``--output-file``: The name of the output JSON file.
    - ``--output-to-stdout``: Output to stdout
    - ``--app-id``: The Advanced Users Only - overwrite Support App ID.
    - ``--api-url``: The Advanced Users Only - overwrite Support API URL.
    - ``--k-value``: The Advanced Users Only - overwrite required API k value.

## Pre-requisites

- valid client-id and client-secret from MyF5.com
- valid client-id and client-secret from iHealth
- valid username and password for the BIG-IP(s)
- valid hostname for the BIG-IP(s)
- TMOS version for each host
- valid serial number for one of the BIG-IP(s) 
  - NOTE: Must be a valid serial number covered under a current support contract
- For proactive support cases, a valid maintenance window (Date and Start/Stop times) must be provided for support awareness. Note that opening a proactive case does not schedule a support engineer to join the bridge; if support is needed during the maintenance window, you must contact support and ask for assistance. Reference the proactive notification case; do not create a new case.

## Usage

There are connectivity tests for each of the APIs that you will be using for these tools. While these tests are optional, they are recommended.

    - bigip_connectivity_test.py
    - myf5_connectivity_test.py
    - ihealth_connectivity_test.py

1. For each BIG-IP, run the bigip_generate_qkview.py tool to generate a QKView on the device.
2. For each BIG-IP, run the bigip_download_qkview.py tool to download the QKView from the device.
3. For each BIG-IP, run the bigip_delete_qkview.py tool to delete the QKView from the device.
4. Run the myf5_create_inputs_file.py tool to create the inputs file for creating a support case on MyF5.com. You may use other tools such as Jinja to create the inputs file, but valid inputs are required. If using another tool to create the inputs file, the myf5_retrieve_case_creation_metadata.py tool can be used to retrieve the metadata needed to validate the inputs. 
5. Run the myf5_create_new_support_case.py tool to create a new support case on MyF5.com. You will be presented with the new case number and a link to the support case in MyF5.com.
6. Run the ihealth_upload_qkviews.py tool to upload the QKViews to iHealth. You can specify the case number so that the qkview is attached to the newly created support case. 
7. Optionally, you may use the myf5_add_comments_to_existing_case.py tool to add comments to the existing support case on MyF5.com.