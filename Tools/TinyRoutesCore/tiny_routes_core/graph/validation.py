from .index import GraphIndex, GraphValidationError

def validate_graph(graph):
    try: GraphIndex.build(graph)
    except GraphValidationError as error: return error.codes
    return ()
