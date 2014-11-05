# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
        
from django.conf import settings

from keystoneclient.v3 import client
from keystoneclient import exceptions as keystoneclient_exceptions    

from openstack_dashboard import api

CREDENTIALS = getattr(settings, 'OPENSTACK_KEYSTONE_ADMIN_CREDENTIALS')
CREDENTIALS['AUTH_URL'] = getattr(settings,'OPENSTACK_KEYSTONE_URL')

def fiware_keystoneclient():
    """Encapsulates all the logic for communicating with the keystone server.

    The IdM has its own admin account in the keystone server, and uses it to perform
    operations like create users, projects, etc. when there is no user with admin rights
    (for example, when user registration) to overcome the Keystone limitations.
    """
    # TODO(garcianavalon) find a way to integrate this with the existng keystone api
    # TODO(garcianavalon)caching and efficiency
    keystone = client.Client(username=CREDENTIALS['USERNAME'], 
                                password=CREDENTIALS['PASSWORD'], 
                                project_name=CREDENTIALS['PROJECT'], 
                                auth_url=CREDENTIALS['AUTH_URL'])
    return keystone

def _find_user(keystone, email=None, name=None):
    # NOTE(garcianavalon) I dont know why but find by email returns a NoUniqueMatch 
    # exception so we do it by hand filtering the python dictionary, 
    # which is extremely inneficient...
    if name:
        user = keystone.users.find(name=name)
        return user
    elif email:
        user_list = keystone.users.list()
        for user in user_list:
            if user.email == email:
                return user
        # consistent behaviour with the keystoneclient api
        msg = "No user matching email=%s." % email
        raise keystoneclient_exceptions.NotFound(404, msg)

def _grant_role(keystone, role, user, project):
    role = keystone.roles.find(name=role)
    keystone.roles.grant(role, user=user, project=project)
    return role

def register_user(name, email, password):
    keystone = fiware_keystoneclient()
    default_domain = keystone.domains.get(CREDENTIALS['DOMAIN'])
    default_project = keystone.projects.create(name, domain=default_domain)
    new_user = keystone.users.create(name,
                                    domain=default_domain,
                                    password=password,
                                    email=email,
                                    default_project=default_project)
    # TODO(garcianavalon) expose the role as a config option
    role = _grant_role(keystone, '_member_', new_user, default_project)
    return new_user
    
def activate_user(user_id):
    keystone = fiware_keystoneclient()
    #default_domain = _get_default_domain(keystone)
    user = keystone.users.get(user_id)
    project = keystone.projects.update(user.default_project_id, enabled=True)
    user = keystone.users.update(user, enabled=True)
    return user

def change_password(user_email,new_password):
    keystone = fiware_keystoneclient()
    user = _find_user(keystone, email=user_email)
    user = keystone.users.update(user, password=new_password, enabled=True)
    return user

def check_user(name):
    keystone = fiware_keystoneclient()
    user = _find_user(keystone, name=name)
    return user

def check_email(email):
    keystone = fiware_keystoneclient()
    user = _find_user(keystone, email=email)
    return user

# ROLES AND PERMISSIONS
def create_role(request, name, is_editable=True, application=None, **kwargs):
    manager = api.keystone.keystoneclient(request, admin=True).fiware_roles
    return manager.create(name=name,
                is_editable=is_editable,
                application=application,
                **kwargs)

def update_role(request, role, name=None, is_editable=True, 
                application=None, **kwargs):
    manager = api.keystone.keystoneclient(request, admin=True).fiware_roles
    return manager.update(role, 
                        name=name,
                        is_editable=is_editable,
                        application=application,
                        **kwargs)
        
def delete_role(request, role):
    manager = api.keystone.keystoneclient(request, admin=True).fiware_roles
    return manager.delete(role)