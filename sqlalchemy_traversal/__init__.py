from sqlalchemy_traversal.interfaces    import ISABase
from sqlalchemy_traversal.interfaces    import ISASession
from sqlalchemy_traversal.interfaces    import ISaver

from datetime                           import datetime
from datetime                           import date
from datetime                           import time

from sqlalchemy.orm                     import class_mapper

import colander
import venusian

def format_colander_errors(e):
    """
    This formats our colander errors in a nice format
    for rendering errors
    """
    values = []

    for child in e.children:
        msg = child.msg

        if msg == None:
            msg = e.asdict()

        error = {
            'name': child.node.title
            , 'id': child.node.name
            , 'error': msg
        }

        values.append(error)

    return values

def get_session(request):
    """
    This is a utility to allow you to extract the session from the pyramid
    registry
    """

    if request.registry.queryUtility(ISASession):
        session = request.registry.getUtility(ISASession)
    else:
        raise Exception(
            "You must register ISASession with your SQLAlchemy "
            + "session in the pyramid registry"
        )

    return session

def get_base(request):
    """
    This is a utility to allow you to extract the SQLAlchemy base from the
    pyramid registry
    """

    if request.registry.queryUtility(ISABase):
        base = request.registry.getUtility(ISABase)
    else:
        raise Exception(
            "You must register ISABase with your SQLAlchemy "
            + "base in the pyramid registry"
        )

    return base

class TraversalBase(object):
    def try_to_json(self, request, attr):
        """
        Try to run __json__ on the given object.
        Raise TypeError is __json__ is missing

        :param request: Pyramid Request object
        :type request: <Request>
        :param obj: Object to JSONify
        :type obj: any object that has __json__ method
        :exception: TypeError
        """

        # check for __json__ method and try to JSONify
        if hasattr(attr, '__json__'):
            return attr.__json__(request)

        # raise error otherwise
        raise TypeError('__json__ method missing on %s' % str(attr))

class JsonSerializableMixin(TraversalBase):
    """
    Converts all the properties of the object into a dict for use in json.
    You can define the following as your class properties.

    _json_eager_load :
        list of which child classes need to be eagerly loaded. This applies
        to one-to-many relationships defined in SQLAlchemy classes.

    _base_blacklist :
        top level blacklist list of which properties not to include in JSON

    _json_blacklist :
        blacklist list of which properties not to include in JSON
    """

    _base_blacklist = ['password', '_json_eager_load', '_request',
        '_base_blacklist', '_json_blacklist'
    ]


    def __json__(self, request):
        """
        Main JSONify method

        :param request: Pyramid Request object
        :type request: <Request>
        :return: dictionary ready to be jsonified
        :rtype: <dict>
        """

        props = {}

        # grab the json_eager_load set, if it exists
        # use set for easy 'in' lookups
        json_eager_load = set(getattr(self, '_json_eager_load', []))

        # now load the property if it exists
        # (does this issue too many SQL statements?)
        for prop in json_eager_load:
            getattr(self, prop, None)

        # we make a copy because the dict will change if the database
        # is updated / flushed
        options = self.__dict__.copy()

        # setup the blacklist
        # use set for easy 'in' lookups
        blacklist = set(getattr(self, '_base_blacklist', []))

        # extend the base blacklist with the json blacklist
        blacklist.update(getattr(self, '_json_blacklist', []))

        for key in options:
            # skip blacklisted properties
            if key in blacklist:
                continue

            # do not include private and SQLAlchemy properties
            if key.startswith(('__', '_sa_')):
                continue

            # format and date/datetime/time properties to isoformat
            obj = getattr(self, key)
            if isinstance(obj, (datetime, date, time)):
                props[key] = obj.isoformat()
                continue

            # get the class property value
            attr = getattr(self, key)

            # let see if we need to eagerly load it
            # this is for SQLAlchemy foreign key fields that
            # indicate with one-to-many relationships
            if key in json_eager_load and attr:
                if hasattr(attr, '_sa_instance_state'):
                    props[key] = self.try_to_json(request, attr)
                else:
                    # jsonify all child objects
                    props[key] = [self.try_to_json(request, x) for x in attr]
                continue

            # convert all non integer strings to string or if string conversion
            # is not possible, convert it to Unicode
            if attr and not isinstance(attr, (int, float)):
                try:
                    props[key] = str(attr)
                except UnicodeEncodeError:
                    props[key] = unicode(attr)  # .encode('utf-8')
                continue

            props[key] = attr

        return props

class ModelCollection(TraversalBase):
    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, key):
        """
        since traversal will be passing keys from the URL they will always
        be strings, so we will assume we want to use the traversal lookup_key
        on the model itself unless the key is an integer, in which case we
        will use standard indexing
        """
        if isinstance(key, (str, unicode)):
            for obj in self.collection:
                data = getattr(obj, obj._traversal_lookup_key)

                if isinstance(data, int):
                    compare_value = int(key)
                else:
                    compare_value = key

                # Does the item in the collection have the lookup_key we
                # are looking for?
                if data == compare_value:
                    obj.__parent__ = self.__parent__
                    if hasattr(self, '_request'):
                        obj._request = self._request

                    return obj

            raise KeyError
        else:
            return self.collection[key]

    def __iter__(self):
        return (x for x in self.collection)

    def __json__(self, request):
        return [self.try_to_json(request, x) for x in self.collection]


class TraversalMixin(JsonSerializableMixin):
    """
    This mixin is used to enable traversal on a specific model.
    """
    _traversal_lookup_key = 'id'

    def _recurse_get_traversal_root(self, obj):
        if hasattr(obj, 'get_class'):
            return obj
        else:
            return self._recurse_get_traversal_root(obj.__parent__)

    def _get_class(self, name):
        """
        This is a recursive function that will search every parent
        until we get to the TraversalRoot so that we can get the
        class name
        """
        root = self._recurse_get_traversal_root(self)

        return root.get_class(name)

    def __getitem__(self, attribute):
        """
        This is where the traversal magic happens for a specific model,
        for instance if we are hitting the URL /api/user/1

        We will have a instance of the User class and will try to get 
        the attribute off of the instance.
        """
        obj = None

        # _request comes from our traversal code
        if hasattr(self, '_request'):
            #TODO: Lets make this less of a hack
            # POST means "create", so we are always looking for a class
            if self._request.method == 'POST' and \
                    self._request.path.endswith(attribute):
                # get an sa mapper class to look up properties on
                # we need to find out which class the attribute is
                # attached to and return that
                mapper = class_mapper(self.__class__, compile=False)
                rel_prop = mapper.get_property(attribute)
                name = rel_prop.target.name
                cls = self._get_class(name)()
                cls.__parent__ = self
                cls._request = self._request

                return cls

        obj = getattr(self, attribute)

        # The model had the specific attribute, so we just need to figure out
        # if we are returning a collection or a single instance
        if obj != None:
            try:
                ignore_types = (str, unicode, int, float,TraversalMixin)
                if not isinstance(obj, ignore_types):
                    # is this is a collection
                    iter(obj)
                    col = ModelCollection(obj)
                    col.__parent__ = self

                    if hasattr(self, '_request'):
                        col._request = self._request

                    return col
            except TypeError as e:
                pass

            return obj

        # throws a 404
        raise KeyError

class register_save(object):
    """
    This is a decorator that matches a Model class with a colander Schema

    If an API is called with a POST or PUT it will first try to run validation
    against the schema before doing anything
    """
    def __init__(self, cls, schema):
        self.cls = cls
        self.schema = schema

    def register(self, scanner, name, wrapped):
        def save(request):
            session = get_session(request)

            if request.is_xhr:
                post_items = request.json.items()
            else:
                post_items = request.POST.items()

            schema = self.schema()
            schema = schema.bind(request=request)

            try:
                data = schema.deserialize(post_items)
            except colander.Invalid as e:
                error_dict = {
                    'has_errors': True,
                    'errors': format_colander_errors(e)
                }

                return dict(error_dict.items() + post_items)

            # cleaned dictionary data from the save function
            result = wrapped(request, data)

            for key, value in result.iteritems():
                setattr(request.context, key, value)

            session.add(request.context)
            session.flush()

            return request.context

        registry = scanner.config.registry
        registry.registerAdapter(save, (self.cls, ), ISaver)

    def __call__(self, wrapped):
        venusian.attach(wrapped, self.register)

        return wrapped

def includeme(config):
    config.scan('sqlalchemy_traversal')
    config.include('sqlalchemy_traversal.routes')
