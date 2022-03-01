from fastkml import kml
from geopy import distance
import networkx as nx
import pandas as pd

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

all_edges = []

def has_numbers(input):
    return any(char.isdigit() for char in input)

def parse_paths():
    with open('data/GenieEdges.kml') as kml_file:
        doc = kml_file.read().encode('utf-8')

    k = kml.KML()
    k.from_string(doc)
    document = list(k.features())
    paths = list(document[0].features())
    
    all_paths = []
    for path in range(len(paths)):
        A, B = paths[path].name.split("_")
        coordinates = paths[path].geometry.coords

        full_distance = 0
        for i in range(1, len(coordinates)):
            full_distance += distance.distance(
                coordinates[i-1][1::-1],
                coordinates[i][1::-1]
                ).feet
        all_paths.append((A, B, full_distance/0.75))
    
    return all_paths

def attraction_matrix(speed = 1, train = False, rides=[]):
    all_paths = parse_paths()
    mirror_paths = [(x[1], x[0], x[2]) for x in all_paths]
    train_paths = [
        ('TrainM', 'TrainN', 300),
        ('TrainN', 'TrainF', 300),
        ('TrainF', 'TrainT', 300),
        ('TrainT', 'TrainM', 300)
    ]

    G = nx.DiGraph()
    G.add_weighted_edges_from(all_paths)
    G.add_weighted_edges_from(mirror_paths)
    G.add_weighted_edges_from(train_paths)

    short_paths = []
    for dist_map in nx.shortest_path_length(G, weight='weight'):
        source = dist_map[0]
        for target, dist in dist_map[1].items():
            if not has_numbers(source + target):
                if target not in ['TrainM','TrainT', 'TrainN', 'TrainF'] and source not in ['TrainM','TrainT', 'TrainN', 'TrainF']:
                    short_paths.append((source, target, dist))
    
    df = pd.DataFrame(short_paths, columns = ['Source', 'Target', 'Distance'])
    piv_df = df.pivot('Source', 'Target', 'Distance')

    data = {}
    data['distance_matrix'] = piv_df.values.tolist()
    data['num_groups'] = 1
    data['starting_node'] = 9
    data['att_names'] = piv_df.columns.tolist()
    
    return data

def print_solution(index_manager, routing_model, solution, data):
    print(f'Best Solution: {solution.ObjectiveValue()/60} feet')
    index = routing_model.Start(0)
    route_output = 'Attraction Route:\n'
    while not routing_model.IsEnd(index):
        att_name = data['att_names'][index_manager.IndexToNode(index)]
        route_output += f' {att_name} -->'
        index = solution.Value(routing_model.NextVar(index))
    att_final = data['att_names'][index_manager.IndexToNode(index)]
    route_output += f' {att_final}\n'
    print(route_output)

def traveling_genie():
    data = attraction_matrix()

    index_manager = (
        pywrapcp.RoutingIndexManager(
            len(data['distance_matrix']),
            data['num_groups'],
            data['starting_node'])
    )

    routing_model = pywrapcp.RoutingModel(index_manager)

    def edge_dist(start_index, end_index):
        start_node = index_manager.IndexToNode(start_index)
        end_node = index_manager.IndexToNode(end_index)
        return data['distance_matrix'][start_node][end_node]

    transit_callback_index = routing_model.RegisterTransitCallback(edge_dist)

    routing_model.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_param = pywrapcp.DefaultRoutingSearchParameters()
    search_param.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    solution = routing_model.SolveWithParameters(search_param)

    if solution:
        print_solution(index_manager, routing_model, solution, attraction_matrix())

# We need to be able to take in a subset of points and only use those
# We need to be able to turn on and off the train shortcut
# We need to be able to add ride times to the equation
# We need to limit how much time that we have in the park


ride_lengths = {
    'Alice': 240,
    'Astro': 90,
    'Autopia': 270,
    'Buzz': 270,
    'Canal': 570,
    'Canoe': 600,
    'Carrousel': 180,
    'Casey': 240,
    'Dumbo': 100,
    'Entrance': 0,
    'Gadget': 60,
    'Indiana': 600,
    'Jungle': 450,
    'Lincoln': 960,
    'Mad': 90,
    'Mansion': 540,
    'Matterhorn': 240,
    'Millenium': 300,
    'Monorail': 900,
    'Nemo': 780,
    'Peter': 180,
    'Pinocchio': 180,
    'Pirates': 900,
    'Pooh': 240,
    'Resistance': 1080,
    'Riverboat': 1080,
    'Roger': 240,
    'Small': 840,
    'Snow': 120,
    'Space': 300,
    'Splash': 660,
    'Thunder': 210,
    'Tiki': 870,
    'Toad': 120,
    'Tours': 420,
    'Vehicles': 420
}


# https://touringplans.com/disneyland/attractions/duration