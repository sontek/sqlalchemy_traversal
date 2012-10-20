from sqlalchemy_traversal import get_session
from sqlalchemy_traversal import get_base
from sqlalchemy_traversal import TraversalMixin
from sqlalchemy_traversal import ModelCollection
from sqlalchemy.orm.exc   import NoResultFound


class SQLAlchemyRoot(object):
    """
    This is a resource factory that wraps a SQL Alchemy class and will set a
    _request attribute on the instance during traversal so that the instance
    may check items on the request such as the method or query string
    """
    def __init__(self, request, cls):
        self.request = request
        self.session = get_session(self.request)
        self.cls = cls

    def __getitem__(self, k):

        try:
            key = getattr(self.cls, self.cls._traversal_lookup_key)

            result =  self.session.query(self.cls).filter(key == k)
            result = result.one()

            # we need give the SQLAlchemy model an instance of the request
            # so that it can check if we are in a PUT or POST
            result._request = self.request

            result.__parent__ = self
            return result
        except NoResultFound as e:
            raise KeyError

class TraversalRoot(object):
    """
    This is the root factory to use on a traversal route:

        config.add_route('api', '/api/*traverse', factory=TraversalRoot)

    You may use it as a standalone factory, you just register your base
    SQLAlchemy object in the pyramid registry with ISABase and your Session
    should be registered with ISASession

        config.registry.registerUtility(base_class, ISABase)
        config.registry.registerUtility(DBSession, ISASession)

    """
    __name__ = None
    __parent__ = None

    def __init__(self, request):
        self.request = request
        self.base = get_base(request)
        self.session = get_session(request)
        self.tables = {}

        # Loop through all the tables in the SQLAlchemy registry
        # and store them if they subclass the TraversalMixin
        for key, table in self.base._decl_class_registry.iteritems():
            if issubclass(table, TraversalMixin):
                table.__parent__ = self
                self.tables[table.__tablename__] = table

    def __getitem__(self, key):
        """
        This is used in traversal to get the correct item. If the path ends
        with a tablename such as "user" then we will return a list of all the
        rows in table wrapped in a ModelCollection.

        If the request is a PUT or POST we will assume that you want to create
        or update the object and will just return an instance of the model.

        If we are in a GET request and don't end with a tablename then we will
        root a SQLAlchemyFactory that will keep track of which node we are 
        currently at.
        """
        cls = self.tables[key]

        to_return = None

        # Do we have the table registered as a traversal object?
        if cls == None:
            raise KeyError

        # This is used to shortcircuit the traversal, if we are ending
        # on a model, for instance /api/user then we should either be creating
        # a new instance or querying the table
        if self.request.path.endswith(key):
            if self.request.method == 'GET':
                to_return = ModelCollection(
                    [x for x in self.session.query(cls).all()]
                )
            elif self.request.method == 'POST' or self.request.method == 'PUT':
                to_return = cls()

        # If we haven't found something to return in the traversal tree yet,
        # it means we want to continue traversing the SQLAlchemy objects,
        # so lets return an SQLAlchemyRoot
        if not to_return:
            to_return = SQLAlchemyRoot(self.request, cls)

        to_return.__parent__ = self

        return to_return
