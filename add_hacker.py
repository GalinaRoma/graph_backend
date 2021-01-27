import json

if __name__ == '__main__':
    with open('devices.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        data['data'].append({
            'id': 'hacker1',
            'name': 'Hacker',
            'type': 'host',
            'networks': [{
                'ip': '10.10.4.10',
                'mask': '255.255.255.252',
            }]
        })
    with open('devices.json', 'w', encoding='utf-8') as f:
        json.dump(data, f)
    with open('edges.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        data['data'].append({
            "id": 'hacker1-h8',
            "first_interfaces_group_id": 'hacker1',
            "second_interfaces_group_id": 'h8'
        })
    with open('edges.json', 'w', encoding='utf-8') as f:
        json.dump(data, f)
