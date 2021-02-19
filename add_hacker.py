import json

if __name__ == '__main__':
    with open('devices.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        data['data'].append({
            'id': 'hacker1',
            'name': 'Unknown',
            'type': 'host',
            "created_at": "2021-02-09T12:10:22.618Z",
            'interfaces': [{
                'ip': '10.10.2.50',
                'mask': '255.255.255.0',
            }]
        })
    with open('devices.json', 'w', encoding='utf-8') as f:
        json.dump(data, f)
    with open('edges.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        data['data'].append({
            "id": 'hacker1-plc2',
            "first_interfaces_group_id": 'hacker1',
            "second_interfaces_group_id": 'plc2',
            "is_approved": False,
            "protocols": ['ICMP', 'telnet', 'SSH', 's7comm']
        })
        data['data'].append({
            "id": 'hacker1-s3',
            "first_interfaces_group_id": 'hacker1',
            "second_interfaces_group_id": 's3',
            "is_approved": False,
            "protocols": ['ICMP', 'telnet', 'SSH', 's7comm']
        })
    with open('edges.json', 'w', encoding='utf-8') as f:
        json.dump(data, f)
