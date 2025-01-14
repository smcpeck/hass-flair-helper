import logging
import time
import requests
import json
import collections
from flair_api import make_client, EmptyBodyException, ApiError

from flair.structures.structure import Structure
from flair.vents.vent import Vent
from flair.pucks.puck import Puck
from flair.rooms.room import Room
from flair.hvac_units.hvac_unit import HvacUnit

_LOGGER = logging.getLogger(__name__)

class FlairSession:

    client_id = ''
    client_secret = ''
    bearer_token = ''
    structures = []
    structure_ids = []
    vents = []
    pucks = []
    rooms = []
    hvac_units = []

SESSION = FlairSession()

class FlairHelper:
    def __init__(self, client_id, client_secret):
        SESSION.client_id = client_id
        SESSION.client_secret = client_secret
        if client_id is None or client_secret is None:
            return None
        else:
            self._authorize()
            self.discover_structures()
            self.discover_vents()
            self.discover_pucks()
            self.discover_rooms()
            self.discover_hvac_units()

    def _authorize(self):
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = requests.post('https://api.flair.co/oauth/token?client_id=' + SESSION.client_id + '&client_secret=' + SESSION.client_secret +
        '&scope=thermostats.view+vents.view+vents.edit+pucks.view+pucks.edit+structures.view+structures.edit&grant_type=client_credentials', headers=headers)
        output = response.json()
        self.response_status = response.status_code
        response.raise_for_status()
        SESSION.bearer_token = output['access_token']

    def structures(self):
        return SESSION.structures

    def vents(self):
        return SESSION.vents

    def pucks(self):
        return SESSION.pucks

    def rooms(self):
        return SESSION.rooms

    def hvac_units(self):
        return SESSION.hvac_units

    def discover_structures(self):
        client = make_client(SESSION.client_id, SESSION.client_secret, 'https://api.flair.co/')
        structures = []
        structure_ids = []
        try:
            structures_list = client.get('structures')
            for structure in structures_list.resources:
                structures.append(Structure(structure, self))
                structure_ids.append(structure.id_)
        except EmptyBodyException:
            pass
        SESSION.structures = structures
        SESSION.structure_ids = structure_ids

    def refresh_structures(self):
        for structure in SESSION.structures:
            structure.refresh()

    def discover_vents(self):
        client = make_client(SESSION.client_id, SESSION.client_secret, 'https://api.flair.co/')
        vents = []
        try:
            vents_list = client.get('vents')
            for vent in vents_list.resources:
                vents.append(Vent(vent, self))
        except EmptyBodyException:
            pass
        SESSION.vents = vents

    def refresh_vents(self):
        for vent in SESSION.vents:
            vent.refresh()

    def vent_current_reading(self, id):
        headers = {
        'Authorization': 'Bearer ' + SESSION.bearer_token
        }
        response = requests.get('https://api.flair.co/api/vents/' + id + '/current-reading', headers=headers)
        output = response.json()
        try:
            error = output['errors'][0]['title']
            if error == 'invalid_token':
                self._authorize()
                self.vent_current_reading(id)
            else:
                return None
        except:
            return output

    def puck_light_level(self, id):
        headers = {
        'Authorization': 'Bearer ' + SESSION.bearer_token
        }
        response = requests.get('https://api.flair.co/api/pucks/' + id + '/current-reading', headers=headers)
        output = response.json()
        try:
            error = output['errors'][0]['title']
            if error == 'invalid_token':
                self._authorize()
                self.puck_light_level(id)
            else:
                return None
        except:
            return output

    def discover_pucks(self):
        client = make_client(SESSION.client_id, SESSION.client_secret, 'https://api.flair.co/')
        pucks = []
        try:
            pucks_list = client.get('pucks')
            for puck in pucks_list.resources:
                pucks.append(Puck(puck, self))
        except EmptyBodyException:
            pass
        SESSION.pucks = pucks

    def refresh_pucks(self):
        for puck in SESSION.pucks:
            puck.refresh()

    def discover_rooms(self):
        client = make_client(SESSION.client_id, SESSION.client_secret, 'https://api.flair.co/')
        rooms = []
        try:
            rooms_list = client.get('rooms')
            for room in rooms_list.resources:
                room_attributes = self.refresh_attributes('rooms', room.id_)
                if (room_attributes.relationships['structure'].data['id'] in SESSION.structure_ids):
                    rooms.append(Room(room, self))
        except EmptyBodyException:
            pass
        SESSION.rooms = rooms

    def refresh_rooms(self):
        for room in SESSION.rooms:
            room.refresh()

    def discover_hvac_units(self):
        client = make_client(SESSION.client_id, SESSION.client_secret, 'https://api.flair.co/')
        hvac_units = []
        try:
            hvac_list = client.get('hvac-units')
            for hvac in hvac_list.resources:
                hvac_units.append(HvacUnit(hvac, self))
        except EmptyBodyException:
            pass
        SESSION.hvac_units = hvac_units

    def refresh_hvac_units(self):
        for hvac_unit in SESSION.hvac_units:
            hvac_unit.refresh()

    def refresh_attributes(self, resource_type, id):
        client = make_client(SESSION.client_id, SESSION.client_secret, 'https://api.flair.co/')
        return client.get(resource_type, id)

    def structure_related_to_room(self, resource_type, id):
        client = make_client(SESSION.client_id, SESSION.client_secret, 'https://api.flair.co/')
        return client.get(resource_type, id)

    def get_schedules(self, id):
        try:
            client = make_client(SESSION.client_id, SESSION.client_secret, 'https://api.flair.co/')
            current_structure = client.get('structures', id)
            return current_structure.get_rel('schedules')
        except:
            return None

    def control_vent(self, vent, resource_type, attributes, relationships):
        client = make_client(SESSION.client_id, SESSION.client_secret, 'https://api.flair.co/')
        id = vent.vent_id
        client.update(resource_type, id, attributes, relationships)

    def control_structure(self, structure, resource_type, attributes, relationships):
        client = make_client(SESSION.client_id, SESSION.client_secret, 'https://api.flair.co/')
        id = structure.structure_id
        client.update(resource_type, id, attributes, relationships)

    def control_room(self, room, resource_type, attributes, relationships):
        client = make_client(SESSION.client_id, SESSION.client_secret, 'https://api.flair.co/')
        id = room.room_id
        client.update(resource_type, id, attributes, relationships)

    def control_hvac(self, hvac, resource_type, attributes, relationships):
        client = make_client(SESSION.client_id, SESSION.client_secret, 'https://api.flair.co/')
        id = hvac.hvac_id
        client.update(resource_type, id, attributes, relationships)

    def get_all_structures(self):
        return SESSION.structures

    def get_all_vents(self):
        return SESSION.vents

    def get_all_pucks(self):
        return SESSION.pucks

    def get_all_rooms(self):
        return SESSION.rooms

