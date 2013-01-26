from sqlalchemy_traversal import get_session
from sqlalchemy_traversal import get_base
from sqlalchemy_traversal import TraversalMixin
from sqlalchemy_traversal import ModelCollection
from sqlalchemy_traversal import filter_query_by_qs
from sqlalchemy_traversal import get_prop_from_cls
from sqlalchemy_traversal import parse_key
from sqlalchemy_traversal import filter_query
from sqlalchemy.orm       import contains_eager
from sqlalchemy.orm.exc   import NoResultFound
from sqlalchemy.exc       import ProgrammingError
from sqlalchemy.exc       import DataError

import urllib

class QueryGetItem(object):
    """
    This is used so that if we haven't ended our traversal we can pass
    unexecuted queries around to limit the amount of queries we actually
    run during traversal
    """
    def __init__(self, cls, query, request, old_gi):
        self.cls = cls
        self.query = query
        self.request = request
        self.session = get_session(self.request)
        self.old_gi = old_gi

    def __call__(self, item):
        cls = get_prop_from_cls(self.cls, item)
        if self.request.path.endswith(item):
            self.query = self.query.outerjoin(item)
            self.query = self.query.options(contains_eager(item))

            self.query = filter_query_by_qs(
                self.session,
                cls,
                self.request.GET,
                existing_query = self.query
            )

            try:
                if self.request.method == 'POST':
                    return cls()

                parent = self.query.one()

                to_return = ModelCollection(
                    [x for x in getattr(parent, item)]
                )
            except ProgrammingError:
                raise KeyError

            return to_return

        new_sa_root = SQLAlchemyRoot(self.request, cls, table_lookup=item)
        new_sa_root.__parent__ = self.__parent__

        return new_sa_root

class SQLAlchemyRoot(object):
    """
    This is a resource factory that wraps a SQL Alchemy class and will set a
    _request attribute on the instance during traversal so that the instance
    may check items on the request such as the method or query string
    """
    def __init__(self, request, cls, table_lookup=None):
        self.request = request
        self.session = get_session(self.request)
        self.cls = cls

        if table_lookup == None:
            self.table_lookup = self.cls.__tablename__
        else:
            self.table_lookup = table_lookup

    def __getitem__(self, k):
        try:
            key = getattr(self.cls, self.cls._traversal_lookup_key)

            result =  self.session.query(self.cls).filter(key == k)

            # This is the final object we want, so lets return the result
            # if its not, lets return the query itself
#            if self.request.path.split('/')[-2] == self.table_lookup:

            try:
                result = filter_query_by_qs(self.session, self.cls,
                        self.request.GET
                        , existing_query = result
                )

                result = result.one()
            except (ProgrammingError, DataError):
                raise KeyError
#                getitem = QueryGetItem(self.cls, result,
#                    self.request, result.__getitem__
#                )
#
#                getitem.__parent__ = self

#                result.__getitem__ =  getitem

            # we need give the SQLAlchemy model an instance of the request
            # so that it can check if we are in a PUT or POST
            result._request = self.request

            result.__parent__ = self

            return result
        except NoResultFound as e:
            # POSTing to the URL with ID already set?
            if self.request.method == 'POST' and self.cls != None:
                cls = self.cls()
                cls.__parent__ = self

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

    def get_class(self, key):
        """
        This function just returns the class directly without running any
        logic
        """
        return self.tables[key]

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
        filters = parse_key(key)

        cls = self.tables[filters['table']]

        to_return = None

        # Do we have the table registered as a traversal object?
        if cls == None:
            raise KeyError

        # This is used to shortcircuit the traversal, if we are ending
        # on a model, for instance /api/user then we should either be creating
        # a new instance or querying the table
        path = urllib.unquote(self.request.path)

        if path.endswith(key):
            if self.request.method == 'GET':
                #query = filter_query_by_qs(self.session, cls,
                #        self.request.GET
                #)
                query = self.session.query(cls)
                query = filter_query(filters, query, cls)

                try:
                    to_return = ModelCollection(
                        [x for x in query.all()]
                        , request=self.request
                    )
                except ProgrammingError:
                    raise KeyError

            elif self.request.method == 'POST' or self.request.method == 'PUT':
                to_return = cls()

        # If we haven't found something to return in the traversal tree yet,
        # it means we want to continue traversing the SQLAlchemy objects,
        # so lets return an SQLAlchemyRoot
        if not to_return:
            to_return = SQLAlchemyRoot(self.request, cls)

        to_return.__parent__ = self

        return to_return
