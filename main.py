import networkx as nx
import json
from Node import *
import copy
import ipaddress
from dateutil import parser

def dumper(obj):
    try:
        return obj.toJSON()
    except Exception:
        return obj.__dict__


def get_network_ip(network):
    full_address = network['ip'] + '/' + network['mask']
    a = ipaddress.ip_interface(full_address)
    return str(a.network)


def create_graph(nodes, layout_name, coordinates=[]):
    g = nx.Graph()
    for node in nodes:
        g.add_node(node)
        for neighbor in node.neighbors:
            found_elems = [i for i in nodes if i.id == neighbor]
            if len(found_elems) > 0:
                [neighbor_node] = found_elems
                g.add_edge(node, neighbor_node)

    pos = nx.nx_agraph.graphviz_layout(g, prog=layout_name)

    for graph_node in g.nodes:
        found_elems = [i for i in nodes if i.id == graph_node.id]
        if len(found_elems) > 0:
            [input_node] = found_elems
            pos_coordinates = pos[graph_node]
            input_node.x = pos_coordinates[0]
            input_node.y = pos_coordinates[1]

    if len(coordinates) > 0:
        for graph_node in g.nodes:
            found_elems = [i for i in nodes if i.id == graph_node.id]
            if len(found_elems) > 0:
                [input_node] = found_elems
                found_elems = [i for i in coordinates if i['id'] == graph_node.id]
                if len(found_elems) > 0:
                    [node_with_coordinates] = found_elems
                    input_node.x = node_with_coordinates['x']
                    input_node.y = node_with_coordinates['y']


def process(layout_name, is_approved=None, date_from=None):
    """ Main function for import in other modules
    data arg will have format
     [
        {
           "id": "03507423-53e1-4ba1-aeb6-41c911aa88f8",
           "first_interfaces_group_id": "ae17be0e-501c-4bdf-8382-120f6844a546",
           "second_interfaces_group_id": "bac2c676-c41e-4148-83ef-bc64f26b72a0",
           "status": false,
           "data_flows_count": 1
        }, ...
     ]
    layout_name arg as default has 'sfdp' value
    all variants are 'sfdp', 'circo', 'dot' """
    # This should be replaced by data arg

    if date_from == 'null' or date_from is None:
        date_from = None
    else:
        date_from = parser.isoparse(date_from)

    with open('edges.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        edges_data = data['data']

    with open('devices.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        devices_data = data['data']

    with open('sfdp_coordinates.json', 'r', encoding='utf-8') as f:
        sfdp_coordinates = json.load(f)

    # get all_nodes for general graph
    all_nodes = []
    for current_device in devices_data:
        current_created_at = parser.isoparse(current_device['created_at'])
        if date_from is not None and current_created_at.toordinal() > date_from.toordinal():
            continue
        node = Node({
            'id': current_device['id'],
            'name': current_device['name'],
            'type': current_device['type'],
            'created_at': current_device['created_at'],
            'neighbors': [],
            'networks': current_device['networks']
        })
        for edge in edges_data:
            if current_device['id'] == edge['first_interfaces_group_id']:
                if is_approved == 'null' or edge['is_approved'] == str(is_approved):
                    node.neighbors.append(edge['second_interfaces_group_id'])
            if current_device['id'] == edge['second_interfaces_group_id']:
                if is_approved == 'null' or edge['is_approved'] == str(is_approved):
                    node.neighbors.append(edge['first_interfaces_group_id'])
        all_nodes.append(node)

    if layout_name == 'sfdp':
        # get nodes separated to 2 levels
        result_nodes_2 = []

        for init_node in all_nodes:
            if init_node.type == 'router':
                result_nodes_2.append(Node({
                    'id': init_node.id,
                    'name': init_node.name,
                    'type': init_node.type,
                    'created_at': init_node.created_at,
                    'neighbors': [],
                    'interfaces': init_node.networks
                }))
            else:
                network = get_network_ip(init_node.networks[0])
                network_node = Node({
                    'id': network,
                    'name': network,
                    'type': 'network',
                    'neighbors': [],
                    'children': []
                })
                try:
                    found_elems = [i for i in result_nodes_2 if i.id == network]
                    if len(found_elems) > 0:
                        [elem] = found_elems
                        index_of_network_in_array = result_nodes_2.index(elem)
                    else:
                        index_of_network_in_array = -1
                except Exception:
                    index_of_network_in_array = -1
                init_node_copy = copy.deepcopy(init_node)
                if index_of_network_in_array != -1:
                    result_nodes_2[index_of_network_in_array].children.append(init_node_copy)
                else:
                    network_node.children.append(init_node_copy)
                    result_nodes_2.append(network_node)

        # After we have two level of network, we should add routers to second level by interface
        for node in result_nodes_2:
            if node.type == 'router':
                for interface in node.interfaces:
                    network = get_network_ip(interface)
                    try:
                        found_elems = [i for i in result_nodes_2 if i.id == network]
                        if len(found_elems) > 0:
                            [elem] = found_elems
                            index_of_network_in_array = result_nodes_2.index(elem)
                        else:
                            index_of_network_in_array = -1
                    except Exception:
                        index_of_network_in_array = -1
                    router_copy = copy.deepcopy(node)
                    if index_of_network_in_array != -1:
                        result_nodes_2[index_of_network_in_array].children.append(router_copy)

        for node in result_nodes_2:
            if node.type == 'network':
                created_at = node.children[0].created_at
                node.created_at = created_at
                # TODO: select between all children

        result_nodes = []

        for node in result_nodes_2:
            if node.type == 'network':
                if len(node.children) == 1:
                    result_nodes.append(node.children[0])
                elif len(node.children) == 2:
                    if node.children[0].type == 'router':
                        result_nodes.append(node.children[1])
                    elif node.children[1].type == 'router':
                        result_nodes.append(node.children[0])
                else:
                    result_nodes.append(node)
            else:
                result_nodes.append(node)

        for current_node in result_nodes:
            if current_node.type == 'network':
                for network_child in current_node.children:
                    # process for get neighbors for network-routers level
                    for child_neighbor_id in network_child.neighbors:
                        found_elems = [i for i in result_nodes if i.id == child_neighbor_id]
                        if len(found_elems) > 0:
                            [child_neighbor_node] = found_elems
                            if child_neighbor_node.type == 'router':
                                # set id of neighbor to network
                                current_node.neighbors.append(child_neighbor_id)
                                # set id of neighbor to router
                                child_neighbor_node.neighbors.append(current_node.id)

                    def is_neighbor_valid(neighbor_id) -> bool:
                        child_neighbor_node = [i for i in all_nodes if i.id == neighbor_id][0]
                        if child_neighbor_node.type != 'router':
                            neighbor_network = get_network_ip(child_neighbor_node.networks[0])
                            return neighbor_network == current_node.id
                        elif child_neighbor_node.type == 'router':
                            return True
                        return False

                    network_child.neighbors = list(filter(is_neighbor_valid, network_child.neighbors))
            elif current_node.type == 'router':
                found_elems = [i for i in all_nodes if i.id == current_node.id]
                if len(found_elems) > 0:
                    [current_router] = found_elems
                    for router_neighbor_id in current_router.neighbors:
                        found_elems = [i for i in result_nodes if i.id == router_neighbor_id]
                        if len(found_elems) > 0:
                            [elem] = found_elems
                            current_node.neighbors.append(elem.id)

    create_graph(all_nodes, layout_name, sfdp_coordinates)
    if layout_name == 'sfdp':
        create_graph(result_nodes, layout_name)
        for node in result_nodes:
            if node.type == 'network':
                create_graph(node.children, layout_name)
        output_filename = 'graph_by_levels.json'
        with open(output_filename, 'w') as outfile:
            json.dump(result_nodes, outfile, default=dumper)

    output_filename = layout_name + 'graph.json'
    with open(output_filename, 'w') as outfile:
        json.dump(all_nodes, outfile, default=dumper)
