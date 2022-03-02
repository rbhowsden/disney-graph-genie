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

def shortest_distances(rides=[], train=False, w_speed=4.7, t_speed=5.9):
    all_paths = parse_paths()

    path_times = []
    for path in all_paths:
        if 'Train' in path[0] or 'Train' in path[1]:
            if train and 'Train' in path[0] and 'Train' in path[1]:
                path_times.append((path[0], path[1], path[2]/t_speed))
            elif not train and 'Train' in path[0] and 'Train' in path[1]:
                continue
            else:
                path_times.append((path[0], path[1], path[2]/w_speed))
                path_times.append((path[1], path[0], path[2]/w_speed))
        else:
            path_times.append((path[0], path[1], path[2]/w_speed))
            path_times.append((path[1], path[0], path[2]/w_speed))

    G = nx.DiGraph()
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
        'Vehicles': 420,
        'Train1': 0,
        'Train2': 0,
        'Train3': 0,
        'Train4': 0,
        'Entrance': 0
    }
    
    filtered_paths = []
    if rides:
        for path in short_paths:
            if path[0] in rides and path[1] in rides:
                filtered_paths.append(
                    (path[0], path[1], path[2] + ride_lengths[path[1]])
                )
    else:
        for path in short_paths:
            filtered_paths.append((path[0], path[1], path[2] + ride_lengths[path[1]]))

    df = pd.DataFrame(filtered_paths, columns = ['Source', 'Target', 'Distance'])
    pivot_df = df.pivot('Source', 'Target', 'Distance')
    
    return pivot_df

#Need to figure out better way to unpack these
def traveling_genie(rides, train, w_speed, t_speed):

    df = shortest_distances(rides, train, w_speed, t_speed)
    distance_matrix = df.values.tolist()
    attraction_names = df.columns.tolist()
    starting_node = attraction_names.index('Entrance')

    index_manager = (
        pywrapcp.RoutingIndexManager(
            len(distance_matrix),
            1,
            starting_node)
    )

    routing_model = pywrapcp.RoutingModel(index_manager)

    def edge_dist(start_index, end_index):
        start_node = index_manager.IndexToNode(start_index)
        end_node = index_manager.IndexToNode(end_index)
        return distance_matrix[start_node][end_node]

    transit_callback_index = routing_model.RegisterTransitCallback(edge_dist)

    routing_model.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_param = pywrapcp.DefaultRoutingSearchParameters()
    search_param.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    solution = routing_model.SolveWithParameters(search_param)

    if solution:
        print(f'Best Solution: {solution.ObjectiveValue()} seconds')
        index = routing_model.Start(0)
        route_output = 'Attraction Route:\n'
        while not routing_model.IsEnd(index):
            att_name = attraction_names[index_manager.IndexToNode(index)]
            route_output += f' {att_name} -->'
            index = solution.Value(routing_model.NextVar(index))
        att_final = attraction_names[index_manager.IndexToNode(index)]
        route_output += f' {att_final}\n'
        print(route_output)

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