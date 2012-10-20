from pyramid.view                       import view_config
from sqlalchemy_traversal               import get_session
from sqlalchemy_traversal               import TraversalMixin
from sqlalchemy_traversal.resources     import SQLAlchemyRoot
from sqlalchemy_traversal.interfaces    import ISaver

from zope.interface             import providedBy

@view_config(
    route_name='traversal_resources',
    renderer='json',
)
def resources_view(request):
    session = get_session(request)

    if request.method == 'GET':
        return request.context
    elif request.method == 'POST' or request.method == 'PUT':
        if isinstance(request.context, SQLAlchemyRoot):
            request.context = request.context.cls()

        saver = request.registry.adapters.lookup(
            [providedBy(request.context)], ISaver
        )

        if saver == None:
            raise Exception("You need to register an ISaver for %s" %
                request.context
            )

        result = saver(request)

        if not isinstance(result, TraversalMixin):
            if 'has_errors' in result:
                request.response_status = '400 Bad Request'

        return result
    elif request.method == 'DELETE':
        session.delete(request.context)
        return {'success': True}

