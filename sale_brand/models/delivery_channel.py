from odoo import fields, models


class DeliveryChannel(models.Model):
    _name = 'delivery.channel'
    _description = 'Delivery Channel'
    _order = 'name'

    name = fields.Char(string='Name', required=True, translate=True)
    active = fields.Boolean(default=True)