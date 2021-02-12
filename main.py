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
    """ Calculate network IP for current address by ip and mask """
    full_address = network['ip'] + '/' + network['mask']
    result_ip = ipaddress.ip_interface(full_address)
    return str(result_ip.network)


def is_device_in_current_network(device, network_address) -> bool:
    """ Check interfaces of device is belong to network"""
    for interface in device.networks:
        interface_network = get_network_ip(interface)
        if interface_network == network_address:
            return True
    return False


def get_child_with_min_created_date(children):
    """ Return child with min created_at attribute """
    child_with_min_created_at = children[0]
    for child in children:
        min_date = parser.isoparse(child_with_min_created_at.created_at)
        child_date = parser.isoparse(child.created_at)
        if child_date < min_date:
            child_with_min_created_at = child
    return child_with_min_created_at


def get_children_with_one_interface(children):
    """ Return children which have only one interface """
    children_with_one_interface = []
    for child in children:
        if len(child.networks) == 1:
            children_with_one_interface.append(child)
    return children_with_one_interface


def add_neighbor(neighbor, neighbors):
    """ Add neighbor and check that it is not neighbor already """
    is_exist = find(neighbors, lambda i: i.neighbor_id == neighbor.neighbor_id)
    if is_exist is None:
        neighbors.append(neighbor)


def find(array, condition):
    """ To find elem in list by any condition """
    found_elems = [i for i in array if condition(i)]
    if len(found_elems) > 0:
        [elem] = found_elems
        return elem


def find_index(array, condition):
    """ To get index of elem in list with any condition """
    try:
        elem = find(array, condition)
        if elem:
            return array.index(elem)
        else:
            return -1
    except ValueError:
        return -1


def create_graph(nodes, layout_name, coordinates=None):
    """ Create graph with nodes with using algorithm for layout with layout_name.
    If list of coordinates is not empty coordinates should be set to nodes.
    """
    g = nx.Graph()
    # Add nodes and edges to graph
    for node in nodes:
        g.add_node(node)
        for neighbor in node.neighbors:
            neighbor_node = find(nodes, lambda i: i.id == neighbor.neighbor_id)
            if neighbor_node:
                g.add_edge(node, neighbor_node)

    # Apply algorithm for layout
    pos = nx.nx_agraph.graphviz_layout(g, prog=layout_name)

    # Set to nodes coordinates which are get from layout algorithm
    for graph_node in g.nodes:
        result_node = find(nodes, lambda i: i.id == graph_node.id)
        if result_node:
            pos_coordinates = pos[graph_node]
            result_node.x = pos_coordinates[0]
            result_node.y = pos_coordinates[1]

    # Set to nodes coordinates which are set and saved earlier
    if coordinates is not None and len(coordinates) > 0:
        for graph_node in g.nodes:
            result_node = find(nodes, lambda i: i.id == graph_node.id)
            if result_node:
                node_with_coordinates = find(coordinates, lambda i: i['id'] == graph_node.id)
                if node_with_coordinates:
                    result_node.x = node_with_coordinates['x']
                    result_node.y = node_with_coordinates['y']


def read_json(file_name):
    with open(file_name, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data


def prepare_data_for_flat_graph(devices_data, edges_data, is_approved, filter_date):
    """ Prepare data for flat graph (sfdp and circo layouts) """
    all_nodes = []
    for current_device in devices_data:
        current_created_at = parser.isoparse(current_device['created_at'])
        # Save only devices which satisfy date_filter
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
            # Save only edges which satisfy is_approved filter
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
    return all_nodes


def prepare_data_for_multilevel_graph(devices_data, edges_data, is_approved, filter_date):
    """ Prepare data for multilevel graph with networks
     First level networks and devices with interfaces from different networks
     Second level networks content with devices with interfaces from different networks """

    all_devices = prepare_data_for_flat_graph(devices_data, edges_data, is_approved, filter_date)

    all_nodes_without_neighbors = []
    for device in all_devices:
        # If device has more than 1 interfaces
        # Then it should be on the border of several networks
        # That`s why we save it to first level
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
            # Create copy of device to create child object and not change input device
            device_copy = copy.deepcopy(device)
            # Save id of original device and fix id to new device
            # For separate device on 1 and 2 levels
            if len(device.networks) > 1:
                device_copy.original_id = device_copy.id
                device_copy.id = device_copy.id + str(network)
            index_of_network_in_array = find_index(all_nodes_without_neighbors, lambda i: i.id == network)
            if index_of_network_in_array != -1:
                all_nodes_without_neighbors[index_of_network_in_array].children.append(device_copy)
            else:
                network_node.children.append(device_copy)
                all_nodes_without_neighbors.append(network_node)

    # Set created_at param to network types as min of children created_at
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
            # Case where no element with all interfaces in network
            # Maybe devices with several interfaces which exist on level 1
            if len(children_with_one_interface) == 0:
                continue
            # Case when one element in network, we should move it to level 1
            elif len(children_with_one_interface) == 1:
                result_nodes_without_neighbors.append(children_with_one_interface[0])
            else:
                result_nodes_without_neighbors.append(node)
        else:
            result_nodes_without_neighbors.append(node)

    # Add neighbors for networks and its children and other devices
    for current_node in result_nodes_without_neighbors:
        if current_node.type == 'network':
            for network_child in current_node.children:
                child_new_neighbors = []
                # Case when adding neighbor for network
                # Network neighbors are its children with several interfaces
                if len(network_child.networks) > 1:
                    for neighbor_connection in network_child.neighbors:
                        neighbor_node = find(all_devices,
                                                   lambda i: i.id == neighbor_connection.neighbor_id)
                        neighbor_in_current_network = is_device_in_current_network(neighbor_node, current_node.id)
                        if neighbor_in_current_network:
                            add_neighbor(NeighborConnection({
                                            'neighbor_id': network_child.original_id,
                                            'approved': neighbor_connection.approved,
                                            'protocols': neighbor_connection.protocols,
                                        }), current_node.neighbors)
                            # Also add to network neighbor network as new neighbor
                            neighbor_node = find(all_devices,
                                                 lambda i: i.id == network_child.original_id)
                            add_neighbor(NeighborConnection({
                                'neighbor_id': current_node.id,
                                'approved': neighbor_connection.approved,
                                'protocols': neighbor_connection.protocols,
                            }), neighbor_node.neighbors)
                # Case to add neighbors for network children
                # Children neighbors only check for belonging to current network
                for child_neighbor_connection in network_child.neighbors:
                    child_neighbor_node = find(result_nodes_without_neighbors,
                                               lambda i: i.id == child_neighbor_connection.neighbor_id)
                    if child_neighbor_node is None:
                        child_neighbor_node = find(all_devices, lambda i: i.id == child_neighbor_connection.neighbor_id)
                        neighbor_in_current_network = is_device_in_current_network(child_neighbor_node, current_node.id)
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
            # Case for devices from first level (not network)
            # Their neighbors only to check they belongings to first level
            new_neighbors = []
            for neighbor in current_node.neighbors:
                neighbor_exist_on_level_one = find(result_nodes_without_neighbors, lambda i: i.id == neighbor.neighbor_id)
                if neighbor_exist_on_level_one:
                    add_neighbor(neighbor, new_neighbors)
            current_node.neighbors = new_neighbors

    return result_nodes_without_neighbors


def process(layout_name, is_approved=None, filter_date=None, is_multilevel=False):
    # Read general data from JSON
    edges_data = read_json('edges.json')['data']
    devices_data = read_json('devices.json')['data']

    # Case if layout name is sfdp
    if layout_name == 'sfdp':
        sfdp_coordinates = read_json('sfdp_coordinates.json')

        nodes_for_flat_graph = prepare_data_for_flat_graph(devices_data, edges_data, is_approved, filter_date)

        create_graph(nodes_for_flat_graph, layout_name, sfdp_coordinates)

        output_filename = layout_name + 'graph.json'
        with open(output_filename, 'w') as outfile:
            json.dump(nodes_for_flat_graph, outfile, default=dumper)

    # Case if layout name is circo
    if layout_name == 'circo':
        circo_coordinates = read_json('circo_coordinates.json')

        nodes_for_flat_graph = prepare_data_for_flat_graph(devices_data, edges_data, is_approved, filter_date)

        create_graph(nodes_for_flat_graph, layout_name, circo_coordinates)

        output_filename = layout_name + 'graph.json'
        with open(output_filename, 'w') as outfile:
            json.dump(nodes_for_flat_graph, outfile, default=dumper)

    # Case if layout name is sfdp and graph should be multigraph
    if is_multilevel:
        multilevel_coordinates = read_json('multilevel_coordinates.json')

        nodes_for_multilevel_graph = prepare_data_for_multilevel_graph(devices_data, edges_data, is_approved, filter_date)

        create_graph(nodes_for_multilevel_graph, layout_name, multilevel_coordinates)

        # Create graph and layout for children lists
        for node in nodes_for_multilevel_graph:
            if node.type == 'network':
                network_with_coordinates = find(multilevel_coordinates, lambda i: i["id"] == node.id)
                children = network_with_coordinates["children"] if network_with_coordinates else None
                create_graph(node.children, layout_name, children)

        output_filename = 'graph_by_levels.json'
        with open(output_filename, 'w') as outfile:
            json.dump(nodes_for_multilevel_graph, outfile, default=dumper)
