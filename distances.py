from fastkml import kml
from geopy import distance
import networkx as nx
import pandas as pd

all_edges = []

def has_numbers(input):
    return any(char.isdigit() for char in input)

with open('data/GenieEdges.kml') as kml_file:
    doc=kml_file.read().encode('utf-8')
    k = kml.KML()
    k.from_string(doc)
    document = list(k.features())
    paths = list(document[0].features())
    for path in range(len(paths)):
        A, B = paths[path].name.split("_")
        coordinates = paths[path].geometry.coords

        full_distance = 0
        for i in range(1, len(coordinates)):
            full_distance += distance.distance(coordinates[i-1][1::-1],
                                               coordinates[i][1::-1]).miles
        all_edges.append((A, B, full_distance))

    G=nx.Graph()
    G.add_weighted_edges_from(all_edges)

    new_edges = []
    for dist_map in nx.shortest_path_length(G, weight='weight'):
        source = dist_map[0]
        for target, dist in dist_map[1].items():
            if not has_numbers(source + target):
                new_edges.append((source, target, dist))

df = pd.DataFrame(new_edges, columns = ['Source', 'Target', 'Distance'])
df.pivot(index='Source', columns='Target', values='Distance')
