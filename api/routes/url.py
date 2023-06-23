from flask_restx import Namespace, Resource, fields, abort
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask import request, redirect
# Local-Directory imports
from ..models import Link
from ..utils.url_validate import validate_url

from .. import cache

# --------------------------------------------------


short_namespace = Namespace("short", description="A namespace for a url shortener")


# serializers
# --------------------------------------------------------------------
url_model = short_namespace.model(
    "url_model",
    {
        "id": fields.Integer(dump_only=True),
        "user_id": fields.Integer(dump_only=True),
        "original_url": fields.String(required=True),
        "short_url": fields.String(dump_only=True),
        "date_created": fields.String(dump_only=True),
    },
)


@short_namespace.route("/short_url")
class Shorten_Url(Resource):
    @short_namespace.expect(url_model)
    @cache.cached(timeout=3600)
    @jwt_required()
    def post(self):

        """Create a new short URL"""
        current_user = get_jwt_identity()

        data = short_namespace.payload
        original_url = data.get("original_url")


        if not original_url.startswith("http://") and not original_url.startswith(
            "https://"
        ):
            original_url = "http://" + original_url

        if not validate_url(original_url):
            abort(400, message="Invalid url")

        if Link.query.filter_by(original_url=original_url).first():
            abort(400, message="Url already exists")
        else:
            link = Link(user_id=current_user, original_url=original_url)
            link.save()

        response = {
            "short_url": f"{request.host_url}{link.short_url}"
        }

        return response, 201


@short_namespace.route("/<short_url>")
class RedirectShortUrl(Resource):
    # @short_namespace.response(302, description="failed response")
    @cache.memoize(timeout=3600)
    def get(self, short_url):
        """Redirect to the original url"""

        url = Link.query.filter_by(short_url=short_url).first()
        if not url:
            abort(404, message="Url not found")

        url.visit += 1
        url.update()

        return redirect(url.original_url)
