sqlalchemy_traversal
====================

This is a pyramid extension that allows you to use traversal with SQLAlchemy objects

To use this you just have to include sqlalchemy_traversal in your pyramid application
by either putting it in your development.ini:

    pyramid.includes = 
        sqlalchemy_traversal

or by including it in your main:

    config.include('sqlalchemy_traversal')


Then you just register your SQLAlchemy session and declarative base:

    from sqlalchemy_traversal.interfaces import ISASession
    from sqlalchemy_traversal.interfaces import ISABase

    config.registry.registerUtility(DBSession, ISASession)
    config.registry.registerUtility(Base, ISABase)


And then place the TraversalMixin on any SQLAlchemy class and it will automatically
be traversed:

    from sqlalchemy_traversal import TraversalMixin
    
    
    class User(TraversalMixin, Base):
        pass


Now you will be able to hit the URL /traverse/user  to get all the users in your database


You can also tell it to load relationships via the _json_eager_load property:

    class User(TraversalMixin, Base):
        _json_eager_load = ['permissions']
