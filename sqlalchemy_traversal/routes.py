from sqlalchemy_traversal.resources import TraversalRoot

def includeme(config):
    config.add_route(
        'traversal_resources'
        , '/traverse/*traverse'
        , factory=TraversalRoot
    )
