from flask import Blueprint

api_v2_bp = Blueprint('api_v2', __name__)

@api_v2_bp.route('/graphql')
def graphql():
    return {'message': 'GraphQL endpoint coming soon'}, 501