#!/usr/bin/env python

DOCUMENTATION = '''
---
module: uni_sg
short_description: create/delete an Storage Group
description:
  - Module to create or delete a storage group
Author: "Court Campbell"
notes:
    - This module has been tested against UNI 8.4.0.4
requirements:
    - requests package
options:
    name:
        description:
            - Storage Group name
        required: True
    uni_user:
        description:
            - The unisphere login account name.
        required: True
    uni_pass:
        description:
            - The unisphere user password.
        required: True
    state:
        description:
            - the state of the Storage Group
        options:
            - present
            - absent
        required: True
    uni_host:
        description:
            - The unisphere https address
            - https://<uni_host>:8443
        required: True
    symm_id:
        description:
            - The symmetrix ID of the array you want to add/remove the SG
        required: True
'''

EXAMPLES = '''
- name: Create an SG
  ovm_vm:
    name: 'TEST_SG'
    uni_user: 'admin'
    uni_pass: 'password'
    uni_host: 'https://<uni_host>:8443'
    symm_id: '0000000000000'
    state: 'present'
'''

WANT_JSON = ''

#==============================================================
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

#==============================================================
def auth(uni_user, uni_pass):
    """ Set authentication-credentials.

    Set Accept and Content-Type headers to application/json to
    tell Unisphere we want json, not XML.
    """
    session = requests.Session()
    session.auth = (uni_user, uni_pass)
    session.verify = False
    session.headers.update({
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    })
    return session

#==============================================================
class UNIRestClient:

    def __init__(self, baseURI, session):
        self.session = session
        self.baseURI = baseURI


    def create_sg(self, symm_id, data):
        response = self.session.post(
            self.baseURI+'/sloprovisioning/symmetrix/'+symm_id+'/storagegroup',
            data=json.dumps(data)
        )
        return response


    def delete_sg(self, symm_id, sg_id):
        response = self.session.delete(
            self.baseURI+'/sloprovisioning/symmetrix/'+symm_id+'/storagegroup/'+sg_id
        )
        return response

    
    def get_sg(self, symm_id, sg_id):
        response = self.session.get(
            self.baseURI+'/sloprovisioning/symmetrix/'+symm_id+'/storagegroup/'+sg_id
        )
        return response.json()


def main():
    changed = False
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(
                choices=['present', 'absent'],required=True),
            name=dict(required=True),
            uni_user=dict(required=True),
            uni_pass=dict(required=True, no_log=True),
            uni_host=dict(
                default='https://127.0.0.1:8443'),
            symm_id=dict(required=True),
        )
    )
    if HAS_REQUESTS is False:
        module.fail_json(
            msg="uni_sg module requires the 'requests' package")

    baseURI = module.params['uni_host']+'/univmax/restapi'
    session = auth(module.params['uni_user'], module.params['uni_pass'])
    client = UNIRestClient(baseURI, session)

    if session.get(baseURI).status_code != 500:
       module.fail_json(msg="Error connecting to unisphere! Check your login credentials or uni_host address")

    storageGroup = client.get_sg(
        module.params['symm_id'],
        module.params['name'])

    result = {}
    result['name'] = module.params['name'].upper()
    result['state'] = module.params['state']
    if module.params['state'] == 'present':
      if storageGroup.get('message') is not None and 'Cannot find Storage Group' in storageGroup['message']:
        output = client.create_sg(module.params['symm_id'],
                 data={"srpId": "SRP_1", "storageGroupId": module.params['name'].upper(),"create_empty_storage_group": True})
        if output.status_code == 200:
          result['changed'] = True
        else:
          module.fail_json(output.text)
      else:
        result['changed'] = False
    
    if module.params['state'] == 'absent':
      if storageGroup.get('storageGroup') is not None and storageGroup['storageGroup'][0]['storageGroupId'] == module.params['name'].upper():
        output = client.delete_sg(module.params['symm_id'],module.params['name'].upper())
        if output.status_code == 204:
          result['changed'] = True
        else:
          module.fail_json(msg=output.text)
      else:
        result['changed'] = False

    module.exit_json(**result)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
