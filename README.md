sqlalchemy_traversal
====================

This is a pyramid extension that allows you to use traversal with SQLAlchemy objects

Demo App here: https://github.com/eventray/sqlalchemy_traversal_demo

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


Saving
==================================
If you want to be able to create data with your API but the content
coming back doesn't exactly match your model or you want to run it through
schema validation first you can use the register save decorator:

    @register_save(MyModel, MySchema):
    def saving_my_model(request, data):
        data['my_prop'] = 'NEW DATA'
        return data

You can also handle data exceptions with exception_handlers:

    def handle_integrity_error(model, exception):
        return {
            'errors': {
                'message': 'That data is not unique'
            }
        }

    @register_save(
        MyModel
        , MySchema
        , exception_handlers={
            IntegrityError: handle_integrity_error
        }
    ):
    def saving_my_model(request, data):
        data['my_prop'] = 'NEW DATA'
        return data
