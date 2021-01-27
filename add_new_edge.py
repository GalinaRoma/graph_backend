import json

if __name__ == '__main__':
    with open('edges.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        data['data'].append({
            "id": 'h51-h8',
            "first_interfaces_group_id": 'h51',
            "second_interfaces_group_id": 'h8'
        })
    with open('edges.json', 'w', encoding='utf-8') as f:
        json.dump(data, f)
