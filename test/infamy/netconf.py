
from collections import namedtuple
from dataclasses import dataclass

import logging
import socket
import sys
import time
import uuid   # For _ncc_get_data() extension

import libyang
import lxml
import netconf_client.connect
import netconf_client.ncclient
from netconf_client.error import RpcError

modinfo_fields = ("identifier", "version", "format", "namespace")
ModInfoTuple = namedtuple("ModInfoTuple", modinfo_fields)
class ModInfo(ModInfoTuple):
    def xmlns(self):
        return f"xmlns:{self.identifier}=\"{self.namespace}\""

NS = {
    "ietf-netconf-monitoring": "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring",
    "nc": "urn:ietf:params:xml:ns:netconf:base:1.0",
}

class Manager(netconf_client.ncclient.Manager):
    """Wrapper for the real manager

    Just ensures that we can enable debugging without issues when
    operating on an IPv6 socket.

    """
    def _fetch_connection_ip(self):
        """Retrieves and stores the connection's local and remote IP"""
        self._local_ip = None
        self._peer_ip = None
        try:
            self._local_ip = self.session.sock.sock.getsockname()[0]
            self._peer_ip  = self.session.sock.sock.getpeername()[0]
        except (AttributeError, socket_error):
            pass

    def _debug(self):
        self.set_logger_level(logging.DEBUG)
        self.logger().addHandler(logging.StreamHandler(sys.stderr))

class NccGetDataReply:
    """Fold in to DataReply class when upstreaming"""
    def __init__(self, raw, ele):
        self.data_ele = ele.find("{urn:ietf:params:xml:ns:yang:ietf-netconf-nmda}data")
        self.data_xml = lxml.etree.tostring(self.data_ele)
        self.raw_reply = raw

@dataclass
class Location:
    host: str
    port: int = 830
    username: str = "admin"
    password: str = "admin"

class Device(object):
    def __init__(self,
                 location: Location,
                 mapping: dict,
                 yangdir: None | str = None):

        self.mapping = mapping
        self.ly = libyang.Context(yangdir)

        self._ncc_init(location)
        self._ly_init(yangdir)
        # self.update_schema()
        self.ncc.dispatch('<factory-default xmlns="urn:infix:factory-default:ns:yang:1.0"/>')

    def _ncc_init(self, location):
        ai = socket.getaddrinfo(location.host, location.port,
                                0, 0, socket.SOL_TCP)
        sock = socket.socket(ai[0][0], ai[0][1], 0)
        sock.settimeout(60)
        print(f"Connecting to mgmt IP {location.host}:{location.port} ...")
        sock.connect(ai[0][4])
        sock.settimeout(None)

        session = netconf_client.connect.connect_ssh(sock=sock,
                                                     username=location.username,
                                                     password=location.password)
        self.ncc = Manager(session)

    def _ly_init(self, yangdir):
        self.ly = libyang.Context(yangdir)

        lib = self.ly.load_module("ietf-yang-library")
        ns = libyang.util.c2str(lib.cdata.ns)

        xml = lxml.etree.tostring(self.ncc.get(filter=f"""
        	<filter type="subtree">
        		<modules-state xmlns="{ns}" />
        	</filter>""").data_ele[0])

        data = self.ly.parse_data("xml", libyang.IOType.MEMORY,
                                  xml, parse_only=True).print_dict()

        self.modules = { m["name"] : m for m in data["modules-state"]["module"] }

        for ms in self.modules.values():
            if ms["conformance-type"] != "implement":
                continue

            mod = self.ly.load_module(ms["name"])

            # TODO: ms["feature"] contains the list of enabled
            # features, so ideally we should only enable the supported
            # ones. However, features can depend on each other, so the
            # naïve looping approach doesn't work.
            mod.feature_enable_all()

    def _modules_in_xpath(self, xpath):
        modnames = []

        # Find all referenced models
        for seg in xpath.split("/"):
            if ":" in seg:
                modname, node = seg.split(":")
                modnames.append(modname)

        return list(filter(lambda m: m["name"] in modnames,
                           self.modules.values()))

    def _ncc_make_rpc(self, guts, msg_id=None):
        if not msg_id:
            msg_id = uuid.uuid4()

        return '<rpc message-id="{id}" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">{guts}</rpc>' \
            .format(guts=guts, id=msg_id).encode("utf-8")

    def _ncc_get_data_rpc(self, datastore="operational", filter=None, msg_id=None):
        pieces = []
        pieces.append('<get-data xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-nmda">')
        pieces.append(f'<datastore xmlns:ds="urn:ietf:params:xml:ns:yang:ietf-datastores">'
                      f'ds:{datastore}'
                      f'</datastore>')
        if filter:
            xmlns = " ".join([f"xmlns:{m['name']}=\"{m['namespace']}\"" for m in self._modules_in_xpath(filter)])
            pieces.append(f'<xpath-filter {xmlns}>{filter}</xpath-filter>')
        pieces.append("</get-data>")
        return self._ncc_make_rpc("".join(pieces), msg_id=msg_id)

    def _get(self, xpath, getter):
        # Figure out which modules we are referencing
        mods = self._modules_in_xpath(xpath)

        # Fetch the data
        xmlns = " ".join([f"xmlns:{m['name']}=\"{m['namespace']}\"" for m in mods])
        filt = f"<filter type=\"xpath\" select=\"{xpath}\" {xmlns} />"
        # pylint: disable=c-extension-no-member
        cfg = lxml.etree.tostring(getter(filter=filt).data_ele[0])

        return self.ly.parse_data_mem(cfg, "xml", parse_only=True)

    def _get_data(self, xpath):
        """Local member wrapper for netconf-client <get-data> RPC"""
        # pylint: disable=protected-access
        (raw, ele) = self.ncc._send_rpc(self._ncc_get_data_rpc(filter=xpath))
        data = NccGetDataReply(raw, ele)
        # pylint: disable=c-extension-no-member
        cfg = lxml.etree.tostring(data.data_ele[0])
        return self.ly.parse_data_mem(cfg, "xml", parse_only=True)

    def get(self, xpath):
        """RPC <get> (legacy NETCONF) fetches config:false data"""
        return self._get(xpath, self.ncc.get)

    def get_dict(self, xpath):
        """Return Python dictionary of <get> RPC data"""
        return self.get(xpath).print_dict()

    def get_data(self, xpath):
        """RPC <get-data> to fetch operational data"""
        return self._get_data(xpath).print_dict()

    def get_config(self, xpath):
        return self._get(xpath, self.ncc.get_config)

    def get_config_dict(self, xpath):
        return self.get_config(xpath).print_dict()

    def put_config(self, edit):
        yang2nc = {
            "none": None,
            "delete": "delete",
        }

        xml = f"<config xmlns=\"{NS['nc']}\" xmlns:nc=\"{NS['nc']}\">" + edit + "</config>"

        # Translate any edit operations from the yang format generated
        # by diffing trees with libyang, to their NETCONF equivalents.
        for src,dst in yang2nc.items():
            xml = xml.replace(f"yang:operation=\"{src}\"",
                              f"nc:operation=\"{dst}\"" if dst else "")

        for _ in range(0,3):
            try:
                self.ncc.edit_config(xml, default_operation='merge')
            except RpcError as _e:
                print(f"Failed sending edit-config RPC: {_e}  Retrying ...")
                time.sleep(1)
                continue
            break

    def put_config_dict(self, modname, edit):
        mod = self.ly.get_module(modname)
        lyd = mod.parse_data_dict(edit, no_state=True)
        return self.put_config(lyd.print_mem("xml", with_siblings=True, pretty=False))

    def put_diff_dicts(self, modname, old, new):
        mod = self.ly.get_module(modname)
        oldd = mod.parse_data_dict(old, no_state=True)
        newd = mod.parse_data_dict(new, no_state=True)
        lyd = oldd.diff(newd)
        return self.put_config(lyd.print_mem("xml", with_siblings=True, pretty=False))

    def call(self, call):
        return self.ncc.dispatch(call)

    def call_dict(self, modname, call):
        mod = self.ly.get_module(modname)
        lyd = mod.parse_data_dict(call, rpc=True)
        return self.call(lyd.print_mem("xml", with_siblings=True, pretty=False))

    def call_action(self, action):
        xml = "<action xmlns=\"urn:ietf:params:xml:ns:yang:1\">" + action + "</action>"
        return self.ncc.dispatch(xml)

    def call_action_dict(self, modname, action):
        mod = self.ly.get_module(modname)
        lyd = mod.parse_data_dict(action, rpc=True)
        return self.call_action(lyd.print_mem("xml", with_siblings=True, pretty=False))
