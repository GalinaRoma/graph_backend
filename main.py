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


def is_neighbor_valid(neighbor, all_nodes, current_node) -> bool:
    child_neighbor_node = [i for i in all_nodes if i.id == neighbor.neighbor_id][0]
    if child_neighbor_node.type != 'router':
        neighbor_network = get_network_ip(child_neighbor_node.networks[0])
        return neighbor_network == current_node.id
    elif child_neighbor_node.type == 'router':
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
        # get nodes separated to 2 levels
        nodes_without_neighbors = []

        for init_node in all_nodes:
            if init_node.type == 'router':
                nodes_without_neighbors.append(Node({
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
                init_node_copy = copy.deepcopy(init_node)
                index_of_network_in_array = find_index(nodes_without_neighbors, lambda i: i.id == network)
                if index_of_network_in_array != -1:
                    nodes_without_neighbors[index_of_network_in_array].children.append(init_node_copy)
                else:
                    network_node.children.append(init_node_copy)
                    nodes_without_neighbors.append(network_node)

        # After we have two level of network, we should add routers to second level by interface
        for node in nodes_without_neighbors:
            if node.type == 'router':
                for interface in node.interfaces:
                    network = get_network_ip(interface)
                    router_copy = copy.deepcopy(node)
                    index_of_network_in_array = find_index(nodes_without_neighbors, lambda i: i.id == network)
                    if index_of_network_in_array != -1:
                        nodes_without_neighbors[index_of_network_in_array].children.append(router_copy)

        for node in nodes_without_neighbors:
            if node.type == 'network':
                created_at = node.children[0].created_at
                node.created_at = created_at
                # TODO: select between all children

        result_nodes = []

        # Create result list of nodes for multilevel graph
        for node in nodes_without_neighbors:
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

        # Set neighbors for networks, it children and routers.
        for current_node in result_nodes:
            if current_node.type == 'network':
                for network_child in current_node.children:
                    # process for get neighbors for network-routers level
                    for child_neighbor in network_child.neighbors:
                        child_neighbor_node = find(result_nodes, lambda i: i.id == child_neighbor.neighbor_id)
                        if child_neighbor_node and child_neighbor_node.type == 'router':
                            # set id of neighbor to network
                            current_node.neighbors.append(child_neighbor)
                            # set id of neighbor to router
                            child_neighbor_node.neighbors.append(NeighborConnection({
                                'neighbor_id': current_node.id,
                                'approved': child_neighbor.approved,
                                'protocols': child_neighbor.protocols,
                            }))
                    # Filter only children with current network
                    network_child.neighbors = list(filter(lambda elem: is_neighbor_valid(elem, all_nodes, current_node), network_child.neighbors))
            elif current_node.type == 'router':
                current_router = find(all_nodes, lambda i: i.id == current_node.id)
                if current_router:
                    for router_neighbor in current_router.neighbors:
                        neighbor = find(result_nodes, lambda i: i.id == router_neighbor.neighbor_id)
                        if neighbor:
                            current_node.neighbors.append(NeighborConnection({
                                'neighbor_id': neighbor.id,
                                'approved': router_neighbor.approved,
                                'protocols': router_neighbor.protocols,
                            }))

    if layout_name == 'sfdp':
        create_graph(all_nodes, layout_name, sfdp_coordinates)
    if layout_name == 'circo':
        create_graph(all_nodes, layout_name, circo_coordinates)
    if layout_name == 'sfdp':
        create_graph(result_nodes, layout_name, multilevel_coordinates)
        for node in result_nodes:
            if node.type == 'network':
                create_graph(node.children, layout_name, multilevel_coordinates)
        output_filename = 'graph_by_levels.json'
        with open(output_filename, 'w') as outfile:
            json.dump(result_nodes, outfile, default=dumper)

    output_filename = layout_name + 'graph.json'
    with open(output_filename, 'w') as outfile:
        json.dump(all_nodes, outfile, default=dumper)
