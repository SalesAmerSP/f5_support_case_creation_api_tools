# F5 Support Case Creation API Tools
Generates a proactive support case using MyF5 and iHealth; includes qkview generation, retrieval and upload to iHealth.

## Toolset

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
    - ``--name``: The name of the QKView to download.

- bigip_delete_qkview.py

    Required arguments:

    - ``--host``: The hostname of the BIG-IP.
    - ``--username``: The username for the BIG-IP.
    - ``--password``: The password for the BIG-IP.
    - ``--id``: The id of the QKView to delete.

### iHealth Tools

- ihealth_list_qkviews.py

    This tool is used to list QKViews on iHealth.

    Required arguments:

- ihealth_upload_qkview.py

    This tool is used to upload a QKView to iHealth.

    Required arguments:

### MyF5.com Tools

- myf5_create_new_support_case.py

    This tool is used to create a new support case on MyF5.com.

- myf5_update_existing_case.py

    This tool is used to update an existing support case on MyF5.com.

