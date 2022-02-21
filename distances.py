from fastkml import kml
from geopy import distance

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
        print(A, B, full_distance)