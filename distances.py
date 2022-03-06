from fastkml import kml
from geopy import distance
import networkx as nx
import pandas as pd

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

all_edges = []

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
        all_paths.append((A, B, full_distance))
    
    return all_paths

def shortest_distances(w_speed=4.7):
    all_paths = parse_paths()
    path_times = [(x[0], x[1], x[2]/w_speed) for x in all_paths]

    G = nx.Graph()
    G.add_weighted_edges_from(path_times)

    short_paths = []
    for dist_map in nx.shortest_path_length(G, weight='weight'):
        source = dist_map[0]
        for target, dist in dist_map[1].items():
            if not any(char.isdigit() for char in source + target):
                short_paths.append((source, target, dist))
    
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
    
    ride_paths = [(x[0], x[1], x[2] + ride_lengths[x[1]]) for x in short_paths]

    df = pd.DataFrame(ride_paths, columns = ['Source', 'Target', 'Distance'])
    pivot_df = df.pivot('Source', 'Target', 'Distance')
    
    return pivot_df

ride_priority = {
    'Alice': 1,
    'Astro': 1,
    'Autopia': 1,
    'Buzz': 1,
    'Canal': 1,
    'Canoe': 1,
    'Carrousel': 1,
    'Casey': 1,
    'Dumbo': 1,
    'Entrance': 0,
    'Gadget': 1,
    'Indiana': 1,
    'Jungle': 1,
    'Lincoln': 1,
    'Mad': 1,
    'Mansion': 1,
    'Matterhorn': 1,
    'Millenium': 1,
    'Monorail': 1,
    'Nemo': 1,
    'Peter': 1,
    'Pinocchio': 1,
    'Pirates': 1,
    'Pooh': 1,
    'Resistance': 1,
    'Riverboat': 1,
    'Roger': 1,
    'Small': 1,
    'Snow': 1,
    'Space': 1,
    'Splash': 1,
    'Thunder': 1,
    'Tiki': 1,
    'Toad': 1,
    'Tours': 1,
    'Vehicles': 1
}

#Need to figure out better way to unpack these
def traveling_genie(ride_priority, hours, w_speed):

    df = shortest_distances(w_speed)
    distance_matrix = df.values.tolist()
    attraction_names = df.columns.tolist()
    starting_node = attraction_names.index('Entrance')
    hours_in_park = hours

    index_manager = (
        pywrapcp.RoutingIndexManager(
            len(distance_matrix),
            1,
            starting_node)
    )

    routing_model = pywrapcp.RoutingModel(index_manager)

    def time_callback(start_index, end_index):
        start_node = index_manager.IndexToNode(start_index)
        end_node = index_manager.IndexToNode(end_index)
        return distance_matrix[start_node][end_node]

    time_callback_index = routing_model.RegisterTransitCallback(time_callback)

    routing_model.SetArcCostEvaluatorOfAllVehicles(time_callback_index)

    routing_model.AddDimensionWithVehicleCapacity(
        time_callback_index,
        0,
        [3600*hours_in_park],
        True,
        'TimeCapacity'
    )

    penalty = 10000
    for node in range(1, len(distance_matrix)):
        routing_model.AddDisjunction(
            [index_manager.NodeToIndex(node)],
            penalty*ride_priority[attraction_names[node]])

    search_param = pywrapcp.DefaultRoutingSearchParameters()
    search_param.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_param.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    #This search paramter affects the outcome rounding at 5 hours.
    search_param.time_limit.FromSeconds(5)

    solution = routing_model.SolveWithParameters(search_param)

    if solution:
        print(f'Objective: {solution.ObjectiveValue()}')
        dropped_attractions = 'Dropped attractions: '
        total_penalty = 0
        for node in range(routing_model.Size()):
            if routing_model.IsStart(node) or routing_model.IsEnd(node):
                continue
            if solution.Value(routing_model.NextVar(node)) == node:
                attraction = attraction_names[node]
                total_penalty += penalty*ride_priority[attraction]
                dropped_attractions += f'{attraction} '
        print(dropped_attractions)
        print(f'Time Allowed: {hours_in_park} hours')
        print('Time Spent in Park: ',
            f'{(solution.ObjectiveValue() - total_penalty)/3600} hours')

        index = routing_model.Start(0)
        route_output = 'Attraction Route:\n'
        while not routing_model.IsEnd(index):
            att_name = attraction_names[index_manager.IndexToNode(index)]
            route_output += f' {att_name} -->'
            index = solution.Value(routing_model.NextVar(index))
        att_final = attraction_names[index_manager.IndexToNode(index)]
        route_output += f' {att_final}\n'
        print(route_output)

# https://touringplans.com/disneyland/attractions/duration