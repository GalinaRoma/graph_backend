from flask import Flask, request
from flask_cors import CORS
from flask_restful import Resource, Api
import json
from main import process

app = Flask(__name__)
CORS(app)
api = Api(app)


class FlatGraph(Resource):
    def get(self):
        args = request.args
        is_approved = args['filter']
        date_from = args['date_from']

        process('sfdp', is_approved, date_from)
        with open('sfdpgraph.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data

    def post(self):
        with open('sfdp_coordinates.json', 'w', encoding='utf-8') as f:
            json.dump(request.get_json(), f)

    def put(self):
        new_node = request.get_json()
        with open('devices.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            data['data'].append({
                'id': new_node['id'],
                'name': new_node['name'],
                'type': new_node['type'],
                'created_at': new_node['created_at'],
                'networks': new_node['networks']
            })
        with open('devices.json', 'w', encoding='utf-8') as f:
            json.dump(data, f)


class CircoGraph(Resource):
    def get(self):
        args = request.args
        is_approved = args['filter']
        date_from = args['date_from']

        process('circo', is_approved, date_from)
        with open('circograph.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data

    def post(self):
        with open('circo_coordinates.json', 'w', encoding='utf-8') as f:
            json.dump(request.get_json(), f)


class MultilevelGraph(Resource):
    def get(self):
        args = request.args
        is_approved = args['filter']
        date_from = args['date_from']
        process('sfdp', is_approved, date_from)
        with open('graph_by_levels.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data

    def post(self):
        with open('multilevel_coordinates.json', 'w', encoding='utf-8') as f:
            json.dump(request.get_json(), f)


api.add_resource(FlatGraph, '/flat-graph')
api.add_resource(CircoGraph, '/circo-graph')
api.add_resource(MultilevelGraph, '/multilevel-graph')

if __name__ == '__main__':
    app.run(debug=True)
