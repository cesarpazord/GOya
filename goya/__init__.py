def create_app(config=None):
    from flask import Flask
    from .config import Config
    from .extensions import db

    app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    db.init_app(app)

    from .crm import models as _crm, routes as crm_routes, admin as admin_routes
    from .crm.seed import asegurar_admin
    from .scm import models as _scm, routes as scm_routes
    from .erp import models as _erp, routes as erp_routes
    from .observer import notificaciones
    from .web import pages
    from .docs import routes as docs_routes

    app.register_blueprint(pages)
    app.register_blueprint(docs_routes.bp)
    app.register_blueprint(crm_routes.bp, url_prefix="/api")
    app.register_blueprint(admin_routes.bp, url_prefix="/api")
    app.register_blueprint(scm_routes.bp, url_prefix="/api")
    app.register_blueprint(erp_routes.bp, url_prefix="/api")
    app.register_blueprint(notificaciones.bp, url_prefix="/api")

    notificaciones.registrar_observadores()

    with app.app_context():
        db.create_all()
        asegurar_admin(app)
    return app
