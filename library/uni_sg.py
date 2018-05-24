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
            - the state of the Storage Group.
        options:
            - present
            - absent
        required: True
    uni_url:
        description:
            - The unisphere https address
            - https://<uni_url>:8443
        required: True
    symm_id:
        description:
            - The symmetrix ID of the array you want to add/remove the SG.
        required: True
    srp_id:
        description:
            - The storage resource pool ID, needed for create.
        required: false
        default: 'SRP_1'
'''

EXAMPLES = '''
- name: Create an SG
  uni_sg:
    name: 'TEST_SG'
    uni_user: 'admin'
    uni_pass: 'password'
    uni_url: 'https://<uni_url>:8443'
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
        if response.status_code == 404:
          return reponse
        elif response.status_code == 204:
          while True: 
            status = self.get_sg(symm_id, sg_id)
            if status.status_code == 200:
              continue
            if status.status_code == 204:
              continue
            elif status.status_code == 500:
              continue
            elif status.status_code == 404:
              return status
              break
            else:
              return status
              break

    
    def get_sg(self, symm_id, sg_id):
        response = self.session.get(
            self.baseURI+'/sloprovisioning/symmetrix/'+symm_id+'/storagegroup/'+sg_id
        )
        return response


def main():
    changed = False
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(
                choices=['present', 'absent'],required=True),
            name=dict(required=True),
            uni_user=dict(required=True),
            uni_pass=dict(required=True, no_log=True),
            uni_url=dict(
                default='https://127.0.0.1:8443'),
            symm_id=dict(required=True),
            srp_id=dict(default='SRP_1'),
        )
    )
    if HAS_REQUESTS is False:
        module.fail_json(
            msg="uni_sg module requires the 'requests' package")

    baseURI = module.params['uni_url']+'/univmax/restapi/84'
    session = auth(module.params['uni_user'], module.params['uni_pass'])
    client = UNIRestClient(baseURI, session)

    if session.get(baseURI).status_code != 500:
       module.fail_json(msg="Error connecting to unisphere! Check your login credentials or uni_url address")

    storageGroup = client.get_sg(
        module.params['symm_id'],
        module.params['name'])

    result = {}
    result['name'] = module.params['name'].upper()
    result['state'] = module.params['state']
    if module.params['state'] == 'present':
      if storageGroup.status_code == 404:
        output = client.create_sg(module.params['symm_id'],
                 data={"srpId": module.params['srp_id'], "storageGroupId": module.params['name'].upper(),
                   "create_empty_storage_group": True,"emulation": "FBA"})
        if output.status_code == 201:
          result['changed'] = True
        else:
          module.fail_json(msg=str(output.status_code)+': '+output.text)
      elif storageGroup.status_code == 200:
        result['changed'] = False
      else:
       module.fail_json(msg=storageGroup.text)
    
    if module.params['state'] == 'absent':
      if storageGroup.status_code == 200:
        output = client.delete_sg(module.params['symm_id'],module.params['name'].upper())
        if output.status_code == 404:
          result['changed'] = True
        else:
          module.fail_json(msg=str(output.status_code)+': '+output.text)
      elif storageGroup.status_code == 404:
        result['changed'] = False
      else:
        module.fail_json(msg=str(storageGroup.status_code)+": "+storageGroup.text) 

    module.exit_json(**result)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
