from pyramid.view                       import view_config
from sqlalchemy_traversal               import ModelCollection
from sqlalchemy_traversal               import get_session
from sqlalchemy_traversal               import TraversalMixin
from sqlalchemy_traversal.resources     import SQLAlchemyRoot
from sqlalchemy_traversal.interfaces    import ISaver

from zope.interface                     import providedBy

def get_parent_keys(obj, pks):
    if hasattr(obj, '__parent__'):
        if hasattr(obj.__parent__, 'pk'):
            pks["%s_pk" % obj.__parent__.__tablename__]  = obj.__parent__.pk

        get_parent_keys(obj.__parent__, pks)


@view_config(
    route_name='traversal_resources',
    renderer='json',
)
def resources_view(request):
    session = get_session(request)

    if request.method == 'GET':
        #TODO: Do we really want to be doing this? :P
        results = request.context.__json__(request)
        parent_pks = {}
        get_parent_keys(request.context, parent_pks)

        if isinstance(request.context, ModelCollection):
            results = []
            for obj in request.context:
                json = obj.__json__(request)
                results.append(dict(json.items() + parent_pks.items()))

            return results
        else:
            return dict(results.items() + parent_pks.items())

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

        if 'serverAttrs' in request.json:
            to_return = {}
            for attr in request.json['serverAttrs']:
                to_return[attr] = getattr(result, attr)

            return to_return

        return result
    elif request.method == 'DELETE':
        session.delete(request.context)
        return {'success': True}

