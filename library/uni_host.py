#!/usr/bin/env python

DOCUMENTATION = '''
---
module: uni_host
short_description: create/delete a Host
description:
  - Module to create or delete a host
Author: "John Knous"
notes:
    - This module has been tested against UNI 8.4.0.4
requirements:
    - requests package
options:
    hostname:
        description:
            - The name of the host you want to add.
        required: True
    initiator_id:
	description:
	    - List of WWNs for the host.
        required: only for a create, ie, state is set to 'present'
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
            - the state of the Host Group.
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
            - The symmetrix ID of the array you want to add/remove the HG.
        required: True
'''

EXAMPLES = '''
- name: Create a new host
  uni_host:
    name: 'host01'
    uni_user: 'admin'
    uni_pass: 'password'
    uni_url: 'https://<uni_url>:8443'
    symm_id: '0000000000000'
    state: 'present'
    initiator_id:
      - '0000000c900000'
      - '0000000cf00000'

- name: Delete host
  uni_host:
    name: 'host01'
    uni_user: 'admin'
    uni_pass: 'password'
    uni_url: 'https://<uni_url>:8443'
    symm_id: '0000000000000'
    state: 'absent'
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


    def create_host(self, symm_id, data):
        response = self.session.post(
            self.baseURI+'/sloprovisioning/symmetrix/'+symm_id+'/host',
            data=json.dumps(data)
        )
        return response


    def delete_host(self, symm_id, host_id):
        response = self.session.delete(
          self.baseURI+'/sloprovisioning/symmetrix/'+symm_id+'/host/'+host_id
        )
        if response.status_code == 404:
          return response
        elif response.status_code == 204:
          while True: 
            status = self.get_host(symm_id, host_id)
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

    
    def get_host(self, symm_id, host_id):
        response = self.session.get(
            self.baseURI+'/sloprovisioning/symmetrix/'+symm_id+'/host/'+host_id
        )
        return response


def main():
    changed = False
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type=str,required=True,choices=['present', 'absent']),
            initiator_id=dict(type=list),
            hostname=dict(type=str,required=True),
            uni_user=dict(type=str,required=True),
            uni_pass=dict(type=str,required=True,no_log=True),
            uni_url=dict( type=str,default='https://127.0.0.1:8443'),
            symm_id=dict(required=True)
        ),
        required_if=(
          ['state', 'present', ['initiator_id']],
        ),
    )
    if HAS_REQUESTS is False:
        module.fail_json(
            msg="uni_host module requires the 'requests' package")

    baseURI = module.params['uni_url']+'/univmax/restapi'
    session = auth(module.params['uni_user'], module.params['uni_pass'])
    client = UNIRestClient(baseURI, session)

    if session.get(baseURI).status_code != 500:
       module.fail_json(msg="Error connecting to unisphere! Check your login credentials or uni_url address")

    host = client.get_host(
        module.params['symm_id'],
        module.params['hostname'])

    result = {}
    result['hostname'] = module.params['hostname'].upper()
    result['state'] = module.params['state']
    if module.params['state'] == 'present':
      if host.status_code == 404:
        output = client.create_host(module.params['symm_id'],
                 data={"hostId": module.params['hostname'].upper(), "initiatorId": module.params['initiator_id']})
        if output.status_code == 200:
          result['changed'] = True
        else:
          module.fail_json(msg=str(output.status_code)+': '+output.text)
      elif host.status_code == 200:
        result['changed'] = False
      else:
       module.fail_json(msg=host.text)
    
    if module.params['state'] == 'absent':
      if host.status_code == 200:
        output = client.delete_host(module.params['symm_id'],module.params['hostname'].upper())
        if output.status_code == 404:
          result['changed'] = True
        else:
          module.fail_json(msg=str(output.status_code)+': '+output.text)
      elif host.status_code == 404:
        result['changed'] = False
      else:
        module.fail_json(msg=str(host.status_code)+": "+host.text) 

    module.exit_json(**result)

# pylint: disable=wrong-import-position
from ansible.module_utils.basic import AnsibleModule
import json
if __name__ == '__main__':
    main()
