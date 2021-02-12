import networkx as nx
import json
from Node import *
from NeighborConnection import *
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


def is_neighbor_in_current_network(neighbor, network) -> bool:
    for interface in neighbor.networks:
        interface_network = get_network_ip(interface)
        if interface_network == network:
            return True
    return False


def find(array, condition):
    found_elems = [i for i in array if condition(i)]
    if len(found_elems) > 0:
        [elem] = found_elems
        return elem


def find_index(array, condition):
    try:
        elem = find(array, condition)
        if elem:
            return array.index(elem)
        else:
            return -1
    except ValueError:
        return -1


def create_graph(nodes, layout_name, coordinates=[]):
    """ Create graph with nodes with using algorithm for layout with layout_name.
    If list of coordinates is not empty coordinates should be set to nodes.
    """
    g = nx.Graph()
    for node in nodes:
        g.add_node(node)
        for neighbor in node.neighbors:
            neighbor_node = find(nodes, lambda i: i.id == neighbor.neighbor_id)
            if neighbor_node:
                g.add_edge(node, neighbor_node)

    pos = nx.nx_agraph.graphviz_layout(g, prog=layout_name)

    for graph_node in g.nodes:
        result_node = find(nodes, lambda i: i.id == graph_node.id)
        if result_node:
            pos_coordinates = pos[graph_node]
            result_node.x = pos_coordinates[0]
            result_node.y = pos_coordinates[1]

    if len(coordinates) > 0:
        for graph_node in g.nodes:
            result_node = find(nodes, lambda i: i.id == graph_node.id)
            if result_node:
                node_with_coordinates = find(coordinates, lambda i: i['id'] == graph_node.id)
                if node_with_coordinates:
                    result_node.x = node_with_coordinates['x']
                    result_node.y = node_with_coordinates['y']


def process(layout_name, is_approved=None, filter_date=None):
    if filter_date == 'null' or filter_date is None:
        filter_date = None
    else:
        filter_date = parser.isoparse(filter_date)

    with open('edges.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        edges_data = data['data']

    with open('devices.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        devices_data = data['data']

    with open('sfdp_coordinates.json', 'r', encoding='utf-8') as f:
        sfdp_coordinates = json.load(f)

    with open('circo_coordinates.json', 'r', encoding='utf-8') as f:
        circo_coordinates = json.load(f)

    with open('multilevel_coordinates.json', 'r', encoding='utf-8') as f:
        multilevel_coordinates = json.load(f)

    # get all_nodes for flat general graph
    all_nodes = []
    for current_device in devices_data:
        current_created_at = parser.isoparse(current_device['created_at'])
        if filter_date is not None and current_created_at.toordinal() > filter_date.toordinal():
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
                if is_approved is None or edge['is_approved'] == is_approved:
                    node.neighbors.append(NeighborConnection({
                        'neighbor_id': edge['second_interfaces_group_id'],
                        'approved': edge['is_approved'],
                        'protocols': edge['protocols']
                    }))
            if current_device['id'] == edge['second_interfaces_group_id']:
                if is_approved is None or edge['is_approved'] == is_approved:
                    node.neighbors.append(NeighborConnection({
                        'neighbor_id': edge['first_interfaces_group_id'],
                        'approved': edge['is_approved'],
                        'protocols': edge['protocols']
                    }))
        all_nodes.append(node)

    if layout_name == 'sfdp':
        result_nodes = process2(all_nodes)

    if layout_name == 'sfdp':
        create_graph(all_nodes, layout_name, sfdp_coordinates)
    if layout_name == 'circo':
        create_graph(all_nodes, layout_name, circo_coordinates)
    if layout_name == 'sfdp':
        create_graph(result_nodes, layout_name, multilevel_coordinates)
        for node in result_nodes:
            if node.type == 'network':
                network_with_coordinates = find(multilevel_coordinates, lambda i: i["id"] == node.id)
                create_graph(node.children, layout_name, network_with_coordinates["children"])
        output_filename = 'graph_by_levels.json'
        with open(output_filename, 'w') as outfile:
            json.dump(result_nodes, outfile, default=dumper)

    output_filename = layout_name + 'graph.json'
    with open(output_filename, 'w') as outfile:
        json.dump(all_nodes, outfile, default=dumper)


def get_child_with_min_created_date(children):
    child_with_min_created_at = children[0]
    for child in children:
        min_date = parser.isoparse(child_with_min_created_at.created_at)
        child_date = parser.isoparse(child.created_at)
        if child_date < min_date:
            child_with_min_created_at = child
    return child_with_min_created_at


def get_children_with_one_interface(children):
    children_with_one_interface = []
    for child in children:
        if len(child.networks) == 1:
            children_with_one_interface.append(child)
    return children_with_one_interface


def add_neighbor(neighbor, neighbors):
    is_exist = find(neighbors, lambda i: i.neighbor_id == neighbor.neighbor_id)
    if is_exist is None:
        neighbors.append(neighbor)



def process2(all_devices):
    all_nodes_without_neighbors = []
    for device in all_devices:
        # if device has more than 1 interfaces
        # then it should be on the border of several networks
        # that`s why we save it to first level
        if len(device.networks) > 1:
            device_copy = copy.deepcopy(device)
            all_nodes_without_neighbors.append(device_copy)
        # check each interface of device and save it to network
        for interface in device.networks:
            network = get_network_ip(interface)
            network_node = Node({
                'id': network,
                'name': network,
                'type': 'network',
                'neighbors': [],
                'children': []
            })
            # create copy of device to create child object and not change input device
            device_copy = copy.deepcopy(device)
            # save id of original device and fix id to new device
            # for separate device on 1 and 2 levels
            if len(device.networks) > 1:
                device_copy.original_id = device_copy.id
                device_copy.id = device_copy.id + str(network)
            index_of_network_in_array = find_index(all_nodes_without_neighbors, lambda i: i.id == network)
            if index_of_network_in_array != -1:
                all_nodes_without_neighbors[index_of_network_in_array].children.append(device_copy)
            else:
                network_node.children.append(device_copy)
                all_nodes_without_neighbors.append(network_node)

    # set created_at param to network types as min of children created_at
    for node in all_nodes_without_neighbors:
        if node.type == 'network':
            child_with_min_created_date = get_child_with_min_created_date(node.children)
            node.created_at = child_with_min_created_date.created_at

    result_nodes_without_neighbors = []

    # Create result list of nodes for multilevel graph
    # Move device from network where only one device to 1 level
    for node in all_nodes_without_neighbors:
        if node.type == 'network':
            children_with_one_interface = get_children_with_one_interface(node.children)
            # case where no element with all interfaces in network
            # maybe devices with several interfaces which exist on level 1
            if len(children_with_one_interface) == 0:
                continue
            # case when one element in network, we should move it to level 1
            elif len(children_with_one_interface) == 1:
                result_nodes_without_neighbors.append(children_with_one_interface[0])
            else:
                result_nodes_without_neighbors.append(node)
        else:
            result_nodes_without_neighbors.append(node)

    for current_node in result_nodes_without_neighbors:
        if current_node.type == 'network':
            for network_child in current_node.children:
                child_new_neighbors = []
                if len(network_child.networks) > 1:
                    for neighbor_connection in network_child.neighbors:
                        neighbor_node = find(all_devices,
                                                   lambda i: i.id == neighbor_connection.neighbor_id)
                        neighbor_in_current_network = is_neighbor_in_current_network(neighbor_node, current_node.id)
                        if neighbor_in_current_network:
                            add_neighbor(NeighborConnection({
                                            'neighbor_id': network_child.original_id,
                                            'approved': neighbor_connection.approved,
                                            'protocols': neighbor_connection.protocols,
                                        }), current_node.neighbors)
                            neighbor_node = find(all_devices,
                                                 lambda i: i.id == network_child.original_id)
                            add_neighbor(NeighborConnection({
                                'neighbor_id': current_node.id,
                                'approved': neighbor_connection.approved,
                                'protocols': neighbor_connection.protocols,
                            }), neighbor_node.neighbors)
                for child_neighbor_connection in network_child.neighbors:
                    child_neighbor_node = find(result_nodes_without_neighbors,
                                               lambda i: i.id == child_neighbor_connection.neighbor_id)
                    if child_neighbor_node is None:
                        child_neighbor_node = find(all_devices, lambda i: i.id == child_neighbor_connection.neighbor_id)
                        neighbor_in_current_network = is_neighbor_in_current_network(child_neighbor_node, current_node.id)
                        if neighbor_in_current_network:
                            if len(child_neighbor_node.networks) > 1:
                                add_neighbor(NeighborConnection({
                                    'neighbor_id': child_neighbor_connection.neighbor_id + str(current_node.id),
                                    'approved': child_neighbor_connection.approved,
                                    'protocols': child_neighbor_connection.protocols,
                                }), child_new_neighbors)
                            else:
                                add_neighbor(child_neighbor_connection, child_new_neighbors)
                network_child.neighbors = child_new_neighbors
        else:
            new_neighbors = []
            for neighbor in current_node.neighbors:
                neighbor_exist_on_level_one = find(result_nodes_without_neighbors, lambda i: i.id == neighbor.neighbor_id)
                if neighbor_exist_on_level_one:
                    add_neighbor(neighbor, new_neighbors)
            current_node.neighbors = new_neighbors

    return result_nodes_without_neighbors
