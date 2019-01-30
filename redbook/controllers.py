# -*- coding: utf-8 -*-
from openerp import http

# class Redbook(http.Controller):
#     @http.route('/redbook/redbook/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/redbook/redbook/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('redbook.listing', {
#             'root': '/redbook/redbook',
#             'objects': http.request.env['redbook.redbook'].search([]),
#         })

#     @http.route('/redbook/redbook/objects/<model("redbook.redbook"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('redbook.object', {
#             'object': obj
#         })



